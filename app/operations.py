from datetime import datetime, timezone

from app.db import db


class OperationsMonitor:
    """Records health checks and opens incidents; it does not deploy or mutate production."""

    def record_check(self, name: str, target: str, healthy: bool, detail: str = ""):
        status = 'healthy' if healthy else 'unhealthy'
        with db() as conn:
            cur = conn.execute("INSERT INTO operational_checks(name,target,status,detail) VALUES(?,?,?,?)", (name,target,status,detail))
            check_id = cur.lastrowid
            incident_id = None
            if not healthy:
                severity = 'high' if name in ('api','worker','database') else 'medium'
                cur = conn.execute("INSERT INTO incidents(check_id,severity,title,detail) VALUES(?,?,?,?)", (check_id,severity,f'{name} unhealthy',detail))
                incident_id = cur.lastrowid
        return {'check_id': check_id, 'status': status, 'incident_id': incident_id}

    def dashboard(self):
        with db() as conn:
            checks = [dict(r) for r in conn.execute("SELECT * FROM operational_checks ORDER BY id DESC LIMIT 50")]
            incidents = [dict(r) for r in conn.execute("SELECT * FROM incidents WHERE status='open' ORDER BY id DESC")]
            jobs = dict(conn.execute("SELECT COUNT(*) total, SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) failed, SUM(CASE WHEN status='queued' THEN 1 ELSE 0 END) queued FROM jobs").fetchone())
        return {'checks': checks, 'open_incidents': incidents, 'jobs': jobs}
