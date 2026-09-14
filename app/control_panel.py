from __future__ import annotations

import json
from datetime import datetime, timezone

from app.db import db

AGENTS = [
    "ceo", "opportunity", "sales", "project_manager", "architect", "developer",
    "coding", "qa", "bug_fix", "code_review", "security", "delivery",
    "customer_communication", "research", "operations",
]


def set_agent_activity(agent: str, status: str, detail: str = "", project_id: int | None = None, job_id: int | None = None):
    with db() as conn:
        conn.execute(
            """INSERT INTO agent_activity(agent,status,detail,project_id,job_id,updated_at)
               VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)
               ON CONFLICT(agent) DO UPDATE SET status=excluded.status, detail=excluded.detail,
               project_id=excluded.project_id, job_id=excluded.job_id, updated_at=CURRENT_TIMESTAMP""",
            (agent, status, detail[:2000], project_id, job_id),
        )


def is_agent_paused(agent: str) -> bool:
    with db() as conn:
        row = conn.execute("SELECT paused FROM agent_controls WHERE agent=?", (agent,)).fetchone()
        return bool(row and row["paused"])


def set_agent_paused(agent: str, paused: bool):
    if agent not in AGENTS:
        raise ValueError("Unknown agent")
    with db() as conn:
        conn.execute(
            """INSERT INTO agent_controls(agent,paused,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)
               ON CONFLICT(agent) DO UPDATE SET paused=excluded.paused, updated_at=CURRENT_TIMESTAMP""",
            (agent, int(paused)),
        )
    return {"agent": agent, "paused": paused}


def control_job(job_id: int, action: str):
    with db() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise ValueError("Job not found")
        if action == "cancel":
            conn.execute("UPDATE jobs SET status='cancelled', lease_until=NULL, locked_by=NULL, updated_at=CURRENT_TIMESTAMP WHERE id=? AND status IN ('queued','running')", (job_id,))
        elif action == "retry":
            conn.execute("UPDATE jobs SET status='queued', available_at=CURRENT_TIMESTAMP, lease_until=NULL, locked_by=NULL, last_error='', updated_at=CURRENT_TIMESTAMP WHERE id=? AND status IN ('failed','cancelled')", (job_id,))
        else:
            raise ValueError("Unsupported action")
        return dict(conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())


def dashboard_snapshot():
    with db() as conn:
        activity_rows = {r["agent"]: dict(r) for r in conn.execute("SELECT * FROM agent_activity")}
        controls = {r["agent"]: bool(r["paused"]) for r in conn.execute("SELECT * FROM agent_controls")}
        jobs = [dict(r) for r in conn.execute("SELECT id,kind,status,attempts,max_attempts,locked_by,last_error,updated_at FROM jobs ORDER BY id DESC LIMIT 30")]
        projects = [dict(r) for r in conn.execute("SELECT id,name,status,created_at FROM projects ORDER BY id DESC LIMIT 20")]
        opportunities = [dict(r) for r in conn.execute("SELECT id,title,source,source_url,score,status,created_at FROM opportunities ORDER BY id DESC LIMIT 50")]
        search_runs = [dict(r) for r in conn.execute("SELECT * FROM search_runs ORDER BY id DESC LIMIT 10")]
        research_missions = [dict(r) for r in conn.execute("SELECT * FROM research_missions ORDER BY id DESC LIMIT 20")]
        research_findings = [dict(r) for r in conn.execute(
            "SELECT f.* FROM research_findings f ORDER BY f.id DESC LIMIT 100")]
        approvals = [dict(r) for r in conn.execute("SELECT id,project_id,kind,status,created_at,'project' AS category FROM approvals WHERE status='pending' ORDER BY id DESC")]
        approvals += [dict(r) for r in conn.execute("SELECT id,opportunity_id AS project_id,kind,status,created_at,'sales' AS category FROM sales_approvals WHERE status='pending' ORDER BY id DESC")]
        approvals += [dict(r) for r in conn.execute("SELECT id,engagement_id AS project_id,kind,status,created_at,'engagement' AS category FROM engagement_approvals WHERE status='pending' ORDER BY id DESC")]
        outbox = [dict(r) for r in conn.execute("SELECT id,opportunity_id,interaction_id,provider,status,created_at FROM outbox_approvals WHERE status='pending' ORDER BY id DESC")]
        invoices = [dict(r) for r in conn.execute("SELECT id,engagement_id,number,currency,amount,status,due_date FROM invoices ORDER BY id DESC LIMIT 20")]
        incidents = [dict(r) for r in conn.execute("SELECT * FROM incidents WHERE status='open' ORDER BY id DESC LIMIT 20")]
        events = [dict(r) for r in conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT 30")]
    agents = []
    for name in AGENTS:
        item = activity_rows.get(name, {"agent": name, "status": "idle", "detail": "", "project_id": None, "job_id": None, "updated_at": None})
        item["paused"] = controls.get(name, False)
        if item["paused"]:
            item["status"] = "paused"
        agents.append(item)
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "agents": agents, "jobs": jobs,
            "projects": projects, "opportunities": opportunities, "search_runs": search_runs,
            "research_missions": research_missions, "research_findings": research_findings,
            "pending_approvals": approvals, "outbox": outbox, "invoices": invoices, "incidents": incidents, "events": events}
