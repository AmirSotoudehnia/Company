import json

from app.agents.opportunity import OpportunityAgent
from app.agents.sales import SalesAgent
from app.db import db


class SalesPipeline:
    def create(self, title: str, brief: str, source: str = "manual", source_url: str = "", budget=None):
        assessment = OpportunityAgent().assess(title, brief, budget)
        proposal = SalesAgent().draft(title, brief, assessment)
        with db() as conn:
            cur = conn.execute(
                "INSERT INTO opportunities(title,brief,source,source_url,budget,score,status,assessment_json,proposal_text) VALUES(?,?,?,?,?,?,?,?,?)",
                (title, brief, source, source_url, budget, assessment.score, proposal.status,
                 json.dumps(assessment.__dict__), proposal.proposal),
            )
            opportunity_id = cur.lastrowid
            if proposal.status == "awaiting_human_approval":
                conn.execute("INSERT INTO sales_approvals(opportunity_id) VALUES(?)", (opportunity_id,))
                conn.execute("INSERT INTO lead_interactions(opportunity_id,direction,channel,subject,body,status) VALUES(?,?,?,?,?,?)", (opportunity_id, "outbound", "draft", f"Proposal: {title}", proposal.proposal, "draft"))
        return self.get(opportunity_id)

    def get(self, opportunity_id: int):
        with db() as conn:
            item = conn.execute("SELECT * FROM opportunities WHERE id=?", (opportunity_id,)).fetchone()
            if not item:
                raise ValueError("Opportunity not found")
            approvals = [dict(r) for r in conn.execute("SELECT * FROM sales_approvals WHERE opportunity_id=? ORDER BY id", (opportunity_id,))]
        result = dict(item)
        result["assessment"] = json.loads(result.pop("assessment_json"))
        result["approvals"] = approvals
        return result
    def list(self):
        with db() as conn:
            return [dict(r) for r in conn.execute("SELECT id,title,source,budget,score,status,created_at FROM opportunities ORDER BY id DESC")]

    def interactions(self, opportunity_id: int):
        with db() as conn:
            if not conn.execute("SELECT 1 FROM opportunities WHERE id=?", (opportunity_id,)).fetchone():
                raise ValueError("Opportunity not found")
            return [dict(r) for r in conn.execute("SELECT * FROM lead_interactions WHERE opportunity_id=? ORDER BY id DESC", (opportunity_id,))]

    def decide(self, opportunity_id: int, approval_id: int, approved: bool, note: str = ""):
        with db() as conn:
            approval = conn.execute(
                "SELECT * FROM sales_approvals WHERE id=? AND opportunity_id=?", (approval_id, opportunity_id)
            ).fetchone()
            if not approval:
                raise ValueError("Sales approval not found")
            status = "approved" if approved else "rejected"
            conn.execute("UPDATE sales_approvals SET status=?, note=? WHERE id=?", (status, note, approval_id))
            next_status = "proposal_approved" if approved else "proposal_rejected"
            conn.execute("UPDATE opportunities SET status=? WHERE id=?", (next_status, opportunity_id))
        return self.get(opportunity_id)
