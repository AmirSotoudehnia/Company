from __future__ import annotations
from app.db import db

class CRM:
    STAGES=("lead","qualified","proposal","negotiation","won","lost")
    def pipeline(self):
        with db() as c:
            return [dict(r) for r in c.execute("SELECT id,title,source,budget,score,status,created_at FROM opportunities ORDER BY score DESC,id DESC")]
    def summary(self):
        with db() as c:
            rows=c.execute("SELECT status,COUNT(*) n,COALESCE(SUM(budget),0) value FROM opportunities GROUP BY status").fetchall()
            return {r["status"]:{"count":r["n"],"value":r["value"]} for r in rows}
