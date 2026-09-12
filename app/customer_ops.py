import json
from datetime import date

from app.db import db


class CustomerOps:
    def onboard(self, opportunity_id, customer_name, email, company, scope, criteria, milestones, budget=None, deadline=None):
        with db() as conn:
            opp = conn.execute("SELECT * FROM opportunities WHERE id=? AND status='proposal_approved'", (opportunity_id,)).fetchone()
            if not opp:
                raise ValueError("Opportunity must have an approved proposal")
            cur = conn.execute("INSERT INTO customers(name,email,company) VALUES(?,?,?)", (customer_name, email, company))
            customer_id = cur.lastrowid
            cur = conn.execute("INSERT INTO engagements(opportunity_id,customer_id,scope,acceptance_json,budget,deadline) VALUES(?,?,?,?,?,?)", (opportunity_id, customer_id, scope, json.dumps(criteria), budget, deadline))
            engagement_id = cur.lastrowid
            for item in milestones:
                conn.execute("INSERT INTO milestones(engagement_id,title,deliverable,due_date) VALUES(?,?,?,?)", (engagement_id, item['title'], item['deliverable'], item.get('due_date')))
            conn.execute("INSERT INTO engagement_approvals(engagement_id,kind,note) VALUES(?,?,?)", (engagement_id, 'scope_commitment', 'Approve scope, budget, deadline, and milestones'))
        return self.get(engagement_id)

    def get(self, engagement_id):
        with db() as conn:
            row = conn.execute("SELECT * FROM engagements WHERE id=?", (engagement_id,)).fetchone()
            if not row: raise ValueError("Engagement not found")
            result = dict(row)
            result['acceptance_criteria'] = json.loads(result.pop('acceptance_json'))
            result['milestones'] = [dict(r) for r in conn.execute("SELECT * FROM milestones WHERE engagement_id=? ORDER BY id", (engagement_id,))]
            result['approvals'] = [dict(r) for r in conn.execute("SELECT * FROM engagement_approvals WHERE engagement_id=? ORDER BY id", (engagement_id,))]
        return result
    def approve_scope(self, engagement_id, approval_id, approved, note=""):
        with db() as conn:
            ap = conn.execute("SELECT * FROM engagement_approvals WHERE id=? AND engagement_id=? AND kind='scope_commitment'", (approval_id, engagement_id)).fetchone()
            if not ap: raise ValueError("Scope approval not found")
            state = 'approved' if approved else 'rejected'
            conn.execute("UPDATE engagement_approvals SET status=?,note=? WHERE id=?", (state, note, approval_id))
            if approved:
                eng = conn.execute("SELECT * FROM engagements WHERE id=?", (engagement_id,)).fetchone()
                opp = conn.execute("SELECT * FROM opportunities WHERE id=?", (eng['opportunity_id'],)).fetchone()
                brief = eng['scope'] + "\nAcceptance criteria: " + eng['acceptance_json']
                cur = conn.execute("INSERT INTO projects(name,brief,risk_level) VALUES(?,?,?)", (opp['title'], brief, 'normal'))
                conn.execute("UPDATE engagements SET status='active',project_id=? WHERE id=?", (cur.lastrowid, engagement_id))
            else:
                conn.execute("UPDATE engagements SET status='scope_rejected' WHERE id=?", (engagement_id,))
        return self.get(engagement_id)

    def request_change(self, engagement_id, description, budget_delta=0, deadline_delta_days=0):
        with db() as conn:
            if not conn.execute("SELECT id FROM engagements WHERE id=?", (engagement_id,)).fetchone(): raise ValueError("Engagement not found")
            cur = conn.execute("INSERT INTO change_requests(engagement_id,description,budget_delta,deadline_delta_days) VALUES(?,?,?,?)", (engagement_id, description, budget_delta, deadline_delta_days))
            change_id = cur.lastrowid
            conn.execute("INSERT INTO engagement_approvals(engagement_id,kind,note) VALUES(?,?,?)", (engagement_id, f'change_request:{change_id}', 'Approve scope/budget/deadline change'))
        return {'change_request_id': change_id, 'status': 'pending'}
