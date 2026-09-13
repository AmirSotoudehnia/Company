from __future__ import annotations

from dataclasses import dataclass
from app.db import db
from app.control_panel import set_agent_activity
from app.company_scheduler import CompanyActionQueue
import json

@dataclass
class CompanyDecision:
    action: str
    reason: str
    entity_id: int | None = None

class CompanyBrain:
    """CEO loop: inspect company state and choose the next safe business action."""
    def snapshot(self):
        with db() as c:
            scalar=lambda sql: int(c.execute(sql).fetchone()[0])
            return {
                "opportunities": scalar("SELECT COUNT(*) FROM opportunities"),
                "qualified": scalar("SELECT COUNT(*) FROM opportunities WHERE status IN ('awaiting_human_approval','proposal_approved')"),
                "pending_sales_approvals": scalar("SELECT COUNT(*) FROM sales_approvals WHERE status='pending'"),
                "engagements": scalar("SELECT COUNT(*) FROM engagements"),
                "active_projects": scalar("SELECT COUNT(*) FROM projects WHERE status NOT IN ('delivered','completed','cancelled')"),
                "queued_jobs": scalar("SELECT COUNT(*) FROM jobs WHERE status='queued'"),
                "open_incidents": scalar("SELECT COUNT(*) FROM incidents WHERE status='open'"),
                "unpaid_invoices": scalar("SELECT COUNT(*) FROM invoices WHERE status IN ('draft','sent','overdue')"),
            }

    def decide(self):
        s=self.snapshot()
        if s["open_incidents"]: return CompanyDecision("resolve_incidents", "Operations has open incidents")
        if s["pending_sales_approvals"]: return CompanyDecision("await_owner_approval", "A commercial commitment needs owner approval")
        if s["active_projects"] or s["queued_jobs"]: return CompanyDecision("deliver_work", "Customer work is active")
        return CompanyDecision("discover_opportunities", "No active delivery work; grow pipeline")

    def tick(self):
        d=self.decide()
        scheduled = CompanyActionQueue().schedule(d.action, d.reason, {"entity_id": d.entity_id})
        set_agent_activity("ceo", "running", f"{d.action}: {d.reason}")
        set_agent_activity("ceo", "completed", f"Decision: {d.action} ? {d.reason}")
        snap=self.snapshot()
        with db() as c:
            c.execute("INSERT INTO company_cycles(decision,reason,snapshot_json) VALUES(?,?,?)", (d.action,d.reason,json.dumps(snap)))
        return {"decision": d.__dict__, "scheduled_action": scheduled, "company": snap}
