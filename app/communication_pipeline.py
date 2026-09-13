from app.agents.customer_communication import CustomerCommunicationAgent
from app.db import db


class CommunicationPipeline:
    def draft_status(self, engagement_id):
        with db() as conn:
            eng = conn.execute("SELECT * FROM engagements WHERE id=?", (engagement_id,)).fetchone()
            if not eng: raise ValueError("Engagement not found")
            customer = conn.execute("SELECT * FROM customers WHERE id=?", (eng['customer_id'],)).fetchone()
            project = conn.execute("SELECT * FROM projects WHERE id=?", (eng['project_id'],)).fetchone() if eng['project_id'] else None
            milestones = [dict(r) for r in conn.execute("SELECT * FROM milestones WHERE engagement_id=?", (engagement_id,))]
            draft = CustomerCommunicationAgent().draft_status(customer['name'], project['name'] if project else 'Pending project', project['status'] if project else eng['status'], milestones)
            cur = conn.execute("INSERT INTO communications(engagement_id,kind,subject,body) VALUES(?,?,?,?)", (engagement_id,draft.kind,draft.subject,draft.body))
            return dict(conn.execute("SELECT * FROM communications WHERE id=?", (cur.lastrowid,)).fetchone())

    def list(self, engagement_id):
        with db() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM communications WHERE engagement_id=? ORDER BY id DESC", (engagement_id,))]
