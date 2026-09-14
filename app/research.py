from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from app.control_panel import is_agent_paused, set_agent_activity
from app.db import db
from app.integrations.tavily import TavilyConnector

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:\+?\d[\d ()-]{6,}\d)")


class ResearchService:
    def __init__(self, connector=None):
        self.connector = connector or TavilyConnector()

    def run(self, prompt: str, limit: int = 10, opportunity_id: int | None = None):
        prompt = prompt.strip()
        if not prompt:
            raise ValueError("Research prompt is required")
        if is_agent_paused("research"):
            raise RuntimeError("Research agent is paused")
        with db() as conn:
            mission_id = conn.execute(
                "INSERT INTO research_missions(prompt,opportunity_id) VALUES(?,?)",
                (prompt, opportunity_id),
            ).lastrowid
        set_agent_activity("research", "running", f"Mission {mission_id}: {prompt[:160]}")
        try:
            results = self.connector.search(prompt, limit)
            created = self._store(mission_id, results)
            with db() as conn:
                conn.execute(
                    "UPDATE research_missions SET status='completed',stage='evidence_collected',"
                    "result_count=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (created, mission_id),
                )
            set_agent_activity("research", "completed", f"Mission {mission_id}: {created} sources")
            return self.get_mission(mission_id)
        except Exception as exc:
            with db() as conn:
                conn.execute(
                    "UPDATE research_missions SET status='failed',error=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (str(exc)[:500], mission_id),
                )
            set_agent_activity("research", "failed", f"Mission {mission_id}: {str(exc)[:300]}")
            raise
    def _store(self, mission_id: int, results: list[dict]) -> int:
        created = 0
        with db() as conn:
            for item in results:
                url = str(item.get("url", ""))[:1000]
                parsed = urlparse(url)
                if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    continue
                content = str(item.get("content", ""))[:6000]
                title = str(item.get("title", urlparse(url).netloc))[:300]
                emails = ", ".join(sorted(set(EMAIL_RE.findall(content))))[:500]
                phones = ", ".join(sorted(set(x.strip() for x in PHONE_RE.findall(content))))[:500]
                confidence = max(0.0, min(float(item.get("score", 0.0)), 1.0))
                cur = conn.execute(
                    "INSERT OR IGNORE INTO research_findings"
                    "(mission_id,title,url,snippet,domain,email,phone,confidence) VALUES(?,?,?,?,?,?,?,?)",
                    (mission_id, title, url, content, parsed.netloc[:200],
                     emails, phones, confidence),
                )
                created += int(cur.rowcount > 0)
        return created

    def get_mission(self, mission_id: int):
        with db() as conn:
            mission = conn.execute("SELECT * FROM research_missions WHERE id=?", (mission_id,)).fetchone()
            if not mission:
                raise ValueError("Research mission not found")
            findings = [dict(row) for row in conn.execute(
                "SELECT * FROM research_findings WHERE mission_id=? ORDER BY confidence DESC,id",
                (mission_id,),
            )]
        result = dict(mission)
        result["findings"] = findings
        return result

    def promote(self, finding_id: int):
        from app.sales_pipeline import SalesPipeline
        with db() as conn:
            finding = conn.execute(
                "SELECT f.*,m.prompt FROM research_findings f JOIN research_missions m ON m.id=f.mission_id "
                "WHERE f.id=?", (finding_id,),
            ).fetchone()
        if not finding:
            raise ValueError("Research finding not found")
        brief = f"Research prompt: {finding['prompt']}\nEvidence: {finding['snippet']}"
        return SalesPipeline().create(
            finding["title"], brief[:10000], "tavily_web_research", finding["url"]
        )
    def enrich_opportunity(self, opportunity_id: int):
        with db() as conn:
            opportunity = conn.execute(
                "SELECT * FROM opportunities WHERE id=?", (opportunity_id,)
            ).fetchone()
        if not opportunity:
            raise ValueError("Opportunity not found")
        query = (
            f"{opportunity['title']} official website email contact company background. "
            f"Context: {opportunity['brief'][:500]}"
        )
        mission = self.run(query, 6, opportunity_id)
        evidence = mission["findings"][:3]
        lines = ["", "---", "Research evidence (verify before sending):"]
        for item in evidence:
            contact = item["email"] or item["phone"] or "contact not found in search snippet"
            lines.append(f"- {item['title']}: {item['url']} | {contact}")
        appendix = "\n".join(lines)
        with db() as conn:
            interaction = conn.execute(
                "SELECT * FROM lead_interactions WHERE opportunity_id=? AND direction='outbound' "
                "ORDER BY id DESC LIMIT 1", (opportunity_id,),
            ).fetchone()
            if interaction and "Research evidence (verify before sending):" not in interaction["body"]:
                conn.execute(
                    "UPDATE lead_interactions SET body=?,status='draft' WHERE id=?",
                    ((interaction["body"] + appendix)[:20000], interaction["id"]),
                )
            conn.execute(
                "UPDATE opportunities SET status='outreach_ready_for_approval' WHERE id=?",
                (opportunity_id,),
            )
        return mission
