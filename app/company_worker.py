from __future__ import annotations

import json
import os
import time
from pathlib import Path

from app.company_brain import CompanyBrain
from app.company_scheduler import CompanyActionQueue
from app.db import db, init_db
from app.integrations.jobtech import JobTechConnector
from app.integrations.local_businesses import LocalBusinessConnector
from app.opportunity_discovery import DiscoveredOpportunity, OpportunityDiscovery
from app.research import ResearchService
from app.revenue_engine import RevenueEngine
from app.runtime_config import get_search

COMPANY_ROOT = Path(os.getenv("COMPANY_ROOT", r"I:\Company")).resolve()
DEFAULT_FEED = COMPANY_ROOT / "data" / "opportunities_feed.json"


def _feed_path() -> Path:
    candidate = Path(os.getenv("OPPORTUNITY_FEED_FILE", str(DEFAULT_FEED))).resolve()
    if candidate != COMPANY_ROOT and COMPANY_ROOT not in candidate.parents:
        raise ValueError("Opportunity feed must stay inside COMPANY_ROOT")
    return candidate


def _discover() -> int:
    items = []
    research_count = 0
    path = _feed_path()
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(raw, list):
            raise ValueError("Opportunity feed must be a JSON array")
        items.extend(DiscoveredOpportunity(
            title=str(item["title"]).strip(),
            brief=str(item["brief"]).strip(),
            source=str(item.get("source", "configured_feed")).strip(),
            source_url=str(item.get("source_url", "")).strip(),
            budget=float(item["budget"]) if item.get("budget") is not None else None,
        ) for item in raw)
    if os.getenv("JOBTECH_ENABLED", "").lower() in {"1", "true", "yes"}:
        search = get_search()
        resolved_mode = _auto_mode(search["query"]) if search["mode"] == "auto" else search["mode"]
        if resolved_mode == "general_web":
            research_count = ResearchService().run(
                search["query"], search["limit"]
            )["result_count"]
        else:
            connector = JobTechConnector() if resolved_mode == "job_ads" else LocalBusinessConnector()
            items.extend(connector.search(search["query"], search["limit"]))
    if not items:
        if research_count:
            return research_count
        raise FileNotFoundError(f"Configure local feed or enable a search provider: {path}")
    return len(OpportunityDiscovery().ingest(items))


def _auto_mode(query: str) -> str:
    normalized = query.casefold()
    job_terms = ("job", "jobs", "vacancy", "hiring", "developer role", "استخدام", "کاریابی", "آگهی کار")
    return "job_ads" if any(term in normalized for term in job_terms) else "general_web"


def search_now(query: str, limit: int = 25, mode: str = "auto"):
    from app.runtime_config import set_search
    config = set_search(query, limit, mode)
    resolved_mode = _auto_mode(config["query"]) if mode == "auto" else mode
    with db() as conn:
        run_id = conn.execute("INSERT INTO search_runs(mode,query) VALUES(?,?)", (resolved_mode, config["query"])).lastrowid
    try:
        if resolved_mode == "general_web":
            mission = ResearchService().run(config["query"], config["limit"])
            found = mission["result_count"]
            inserted = found
        else:
            connector = JobTechConnector() if resolved_mode == "job_ads" else LocalBusinessConnector()
            items = connector.search(config["query"], config["limit"])
            inserted_items = OpportunityDiscovery().ingest(items)
            found, inserted = len(items), len(inserted_items)
            mission = None
        with db() as conn:
            conn.execute("UPDATE search_runs SET status='completed',found=?,new_count=?,finished_at=CURRENT_TIMESTAMP WHERE id=?", (found, inserted, run_id))
        return {**config, "resolved_mode": resolved_mode, "mission_id": mission["id"] if mission else None,
                "run_id": run_id, "status": "completed", "found": found, "new": inserted}
    except Exception as exc:
        with db() as conn:
            conn.execute("UPDATE search_runs SET status='failed',error=?,finished_at=CURRENT_TIMESTAMP WHERE id=?", (str(exc)[:500], run_id))
        raise


def run_once():
    brain_result = CompanyBrain().tick()
    queue = CompanyActionQueue()
    action = queue.claim()
    if not action:
        return {"brain": brain_result, "action": None}
    try:
        if action["action"] == "discover_revenue_opportunities":
            with db() as conn:
                saved = conn.execute(
                    "SELECT value FROM runtime_settings WHERE key='revenue_objective'"
                ).fetchone()
            if not saved:
                result = queue.finish(
                    action["id"], "waiting_human",
                    "Enter a revenue objective in the control panel first",
                )
            else:
                mission = RevenueEngine().search(saved["value"], 12)
                result = queue.finish(
                    action["id"], "completed",
                    f"revenue_mission={mission['id']}; candidates={mission['candidate_count']}",
                )
        elif action["action"] == "discover_opportunities":
            count = _discover()
            result = queue.finish(action["id"], "completed", f"legacy_ingested={count}")
        elif action["action"] == "research_opportunity":
            payload = json.loads(action["payload_json"])
            mission = ResearchService().enrich_opportunity(int(payload["opportunity_id"]))
            result = queue.finish(action["id"], "completed", f"mission={mission['id']}; sources={mission['result_count']}")
        else:
            result = queue.finish(action["id"], "waiting_human", "owner approval or configured connector required")
    except FileNotFoundError as exc:
        result = queue.finish(action["id"], "waiting_human", str(exc))
    except Exception as exc:
        result = queue.finish(action["id"], "failed", str(exc)[:500])
    return {"brain": brain_result, "action": result}


def run_forever(interval_seconds: float | None = None):
    init_db()
    interval = interval_seconds or float(os.getenv("COMPANY_TICK_SECONDS", "300"))
    while True:
        run_once()
        time.sleep(max(interval, 10))


if __name__ == "__main__":
    run_forever()
