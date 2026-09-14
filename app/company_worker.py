from __future__ import annotations

import json
import os
import time
from pathlib import Path

from app.company_brain import CompanyBrain
from app.company_scheduler import CompanyActionQueue
from app.db import init_db
from app.integrations.jobtech import JobTechConnector
from app.opportunity_discovery import DiscoveredOpportunity, OpportunityDiscovery

COMPANY_ROOT = Path(os.getenv("COMPANY_ROOT", r"I:\Company")).resolve()
DEFAULT_FEED = COMPANY_ROOT / "data" / "opportunities_feed.json"


def _feed_path() -> Path:
    candidate = Path(os.getenv("OPPORTUNITY_FEED_FILE", str(DEFAULT_FEED))).resolve()
    if candidate != COMPANY_ROOT and COMPANY_ROOT not in candidate.parents:
        raise ValueError("Opportunity feed must stay inside COMPANY_ROOT")
    return candidate


def _discover() -> int:
    items = []
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
        query = os.getenv("JOBTECH_QUERY", "software developer")
        limit = int(os.getenv("JOBTECH_LIMIT", "25"))
        items.extend(JobTechConnector().search(query, limit))
    if not items:
        raise FileNotFoundError(f"Configure local feed or enable JobTech: {path}")
    return len(OpportunityDiscovery().ingest(items))


def run_once():
    brain_result = CompanyBrain().tick()
    queue = CompanyActionQueue()
    action = queue.claim()
    if not action:
        return {"brain": brain_result, "action": None}
    try:
        if action["action"] == "discover_opportunities":
            count = _discover()
            result = queue.finish(action["id"], "completed", f"ingested={count}")
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
