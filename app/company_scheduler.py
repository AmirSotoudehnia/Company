from __future__ import annotations

import json

from app.db import db


class CompanyActionQueue:
    """Durable, deduplicated queue for safe company-level actions."""

    def schedule(self, action: str, reason: str, payload: dict | None = None):
        with db() as conn:
            existing = conn.execute(
                "SELECT * FROM company_actions WHERE action=? AND status IN ('pending','running') ORDER BY id DESC LIMIT 1",
                (action,),
            ).fetchone()
            if existing:
                return dict(existing)
            cur = conn.execute(
                "INSERT INTO company_actions(action,reason,payload_json) VALUES(?,?,?)",
                (action, reason, json.dumps(payload or {})),
            )
            return dict(conn.execute("SELECT * FROM company_actions WHERE id=?", (cur.lastrowid,)).fetchone())

    def list(self, limit: int = 50):
        with db() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT * FROM company_actions ORDER BY id DESC LIMIT ?", (limit,)
            )]
