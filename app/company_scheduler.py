from __future__ import annotations

import json

from app.db import db


class CompanyActionQueue:
    """Durable, deduplicated queue for safe company-level actions."""

    def schedule(self, action: str, reason: str, payload: dict | None = None):
        payload_json = json.dumps(payload or {}, sort_keys=True)
        with db() as conn:
            existing = conn.execute(
                "SELECT * FROM company_actions WHERE action=? AND payload_json=? "
                "AND status IN ('pending','running','waiting_human') ORDER BY id DESC LIMIT 1",
                (action, payload_json),
            ).fetchone()
            if existing:
                return dict(existing)
            cur = conn.execute(
                "INSERT INTO company_actions(action,reason,payload_json) VALUES(?,?,?)",
                (action, reason, payload_json),
            )
            return dict(conn.execute("SELECT * FROM company_actions WHERE id=?", (cur.lastrowid,)).fetchone())

    def claim(self):
        with db() as conn:
            row = conn.execute("SELECT * FROM company_actions WHERE status='pending' ORDER BY id LIMIT 1").fetchone()
            if not row:
                return None
            conn.execute("UPDATE company_actions SET status='running',attempts=attempts+1,updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='pending'", (row["id"],))
            return dict(conn.execute("SELECT * FROM company_actions WHERE id=?", (row["id"],)).fetchone())

    def finish(self, action_id: int, status: str, detail: str = ""):
        if status not in {"completed", "failed", "waiting_human"}:
            raise ValueError("Invalid company action status")
        with db() as conn:
            conn.execute("UPDATE company_actions SET status=?,reason=reason || ?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (status, f" | {detail}" if detail else "", action_id))
            return dict(conn.execute("SELECT * FROM company_actions WHERE id=?", (action_id,)).fetchone())

    def list(self, limit: int = 50):
        with db() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT * FROM company_actions ORDER BY id DESC LIMIT ?", (limit,)
            )]
