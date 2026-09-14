from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from app.control_panel import is_agent_paused, set_agent_activity
from app.db import db
from app.integrations.tavily import TavilyConnector

FREELANCE_HOSTS = {
    "upwork.com", "www.upwork.com", "freelancer.com", "www.freelancer.com",
    "peopleperhour.com", "www.peopleperhour.com", "guru.com", "www.guru.com",
}
REQUEST_MARKERS = (
    "looking for", "need a", "we need", "seeking", "project", "proposal",
    "budget", "fixed price", "hourly", "behöver", "söker",
)


@dataclass(frozen=True)
class RevenuePlan:
    kind: str
    queries: list[tuple[str, str]]
    explanation: str


def classify_revenue_prompt(prompt: str) -> RevenuePlan:
    text = prompt.casefold()
    trade = ("buy", "sell", "buyer", "seller", "import", "export",
             "خرید", "فروش", "خریدار", "فروشنده", "صادرات", "واردات", "نفت")
    freelance = ("freelance", "upwork", "freelancer", "project", "پروژه", "فریلنس")
    service = ("seo", "سئو", "website", "وب سایت", "وب‌سایت",
               "redesign", "طراحی", "اپ", "app")
    if any(term in text for term in trade):
        return RevenuePlan("trade_match", [
            (f"verified sellers suppliers {prompt}", "seller"),
            (f"verified buyers procurement demand {prompt}", "buyer"),
        ], "Find both sides; calculate profit only after terms and compliance data exist.")
    if any(term in text for term in freelance):
        return RevenuePlan("freelance_project", [
            (f"active client project request budget proposal {prompt}", "client"),
        ], "Find direct project requests, not employment advertisements.")
    if any(term in text for term in service):
        return RevenuePlan("service_lead", [
            (f"businesses with demonstrated need for {prompt}", "client"),
        ], "Find businesses with evidence of a service need; technical audit is required.")
    return RevenuePlan("revenue_research", [
        (f"commercial opportunity buyer client budget {prompt}", "counterparty"),
    ], "Research monetizable demand and identify missing verification data.")


class RevenueEngine:
    def __init__(self, connector=None):
        self.connector = connector or TavilyConnector()

    def search(self, prompt: str, limit: int = 10) -> dict:
        prompt = prompt.strip()
        if not prompt:
            raise ValueError("Revenue objective is required")
        if is_agent_paused("opportunity"):
            raise RuntimeError("Opportunity agent is paused")
        plan = classify_revenue_prompt(prompt)
        with db() as conn:
            conn.execute(
                "UPDATE company_actions SET status='completed',"
                "reason=reason || ' | objective supplied in panel',updated_at=CURRENT_TIMESTAMP "
                "WHERE action='discover_revenue_opportunities' AND status='waiting_human'"
            )
            conn.execute(
                "INSERT INTO runtime_settings(key,value,updated_at) "
                "VALUES('revenue_objective',?,CURRENT_TIMESTAMP) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=CURRENT_TIMESTAMP",
                (prompt,),
            )
            mission_id = conn.execute(
                "INSERT INTO revenue_missions(prompt,kind,plan_text) VALUES(?,?,?)",
                (prompt, plan.kind, plan.explanation),
            ).lastrowid
        set_agent_activity("opportunity", "running", f"Revenue mission {mission_id}: {plan.kind}")
        try:
            per_query = max(1, min(20, limit // len(plan.queries) or 1))
            found = 0
            for query, role in plan.queries:
                found += self._store(mission_id, plan.kind, role,
                                     self.connector.search(query, per_query))
            with db() as conn:
                conn.execute(
                    "UPDATE revenue_missions SET status='completed',stage='verification_required',"
                    "candidate_count=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (found, mission_id),
                )
            set_agent_activity("opportunity", "completed",
                               f"Revenue mission {mission_id}: {found} candidates need verification")
            return self.get(mission_id)
        except Exception as exc:
            with db() as conn:
                conn.execute(
                    "UPDATE revenue_missions SET status='failed',error=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (str(exc)[:500], mission_id),
                )
            set_agent_activity("opportunity", "failed", f"Revenue mission {mission_id}: {str(exc)[:250]}")
            raise
    def _store(self, mission_id: int, kind: str, role: str, results: list[dict]) -> int:
        count = 0
        with db() as conn:
            for item in results:
                url = str(item.get("url", ""))[:1000]
                parsed = urlparse(url)
                if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    continue
                title = str(item.get("title", parsed.netloc))[:300]
                snippet = str(item.get("content", ""))[:6000]
                status, reason = self._initial_verdict(kind, parsed.netloc.casefold(), snippet)
                cur = conn.execute(
                    "INSERT OR IGNORE INTO revenue_candidates"
                    "(mission_id,kind,role,title,summary,source_url,source_domain,"
                    "verification_status,verification_reason,risk_status) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (mission_id, kind, role, title, snippet, url, parsed.netloc[:200],
                     status, reason, "review_required"),
                )
                count += int(cur.rowcount > 0)
        return count

    @staticmethod
    def _initial_verdict(kind: str, host: str, snippet: str) -> tuple[str, str]:
        text = snippet.casefold()
        if kind == "freelance_project" and host in FREELANCE_HOSTS:
            if any(marker in text for marker in REQUEST_MARKERS):
                return ("source_verified",
                        "Direct project language appears on a known marketplace; client identity, availability and terms still require verification.")
        if kind == "service_lead":
            return ("needs_technical_audit",
                    "Search relevance is not proof of an SEO or website problem; no contact data will be exposed.")
        if kind == "trade_match":
            return ("needs_due_diligence",
                    "Counterparty identity, authority, product, price, logistics, sanctions and funds are unverified.")
        return ("research_only",
                "Commercial demand, counterparty identity and financial terms are not yet proven.")
    def get(self, mission_id: int) -> dict:
        with db() as conn:
            mission = conn.execute(
                "SELECT * FROM revenue_missions WHERE id=?", (mission_id,)
            ).fetchone()
            if not mission:
                raise ValueError("Revenue mission not found")
            candidates = [dict(row) for row in conn.execute(
                "SELECT * FROM revenue_candidates WHERE mission_id=? ORDER BY id",
                (mission_id,),
            )]
        result = dict(mission)
        result["candidates"] = candidates
        return result

    def promote(self, candidate_id: int):
        with db() as conn:
            candidate = conn.execute(
                "SELECT * FROM revenue_candidates WHERE id=?", (candidate_id,)
            ).fetchone()
        if not candidate:
            raise ValueError("Revenue candidate not found")
        if candidate["verification_status"] != "verified":
            raise ValueError("Only fully verified revenue opportunities can enter sales")
        from app.sales_pipeline import SalesPipeline
        return SalesPipeline().create(
            candidate["title"], candidate["summary"],
            f"revenue_{candidate['kind']}", candidate["source_url"],
        )
