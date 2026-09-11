from __future__ import annotations

import json
from typing import Any

from app.db import db


def audit(tenant_id: int, actor: str, action: str, subject: str = "", repository_id: int | None = None, detail: dict[str, Any] | None = None) -> None:
    with db() as conn:
        conn.execute(
            "INSERT INTO audit_logs(tenant_id,repository_id,actor,action,subject,detail_json) VALUES(?,?,?,?,?,?)",
            (tenant_id, repository_id, actor, action, subject, json.dumps(detail or {}, ensure_ascii=False, sort_keys=True)),
        )


def list_audit(tenant_id: int, limit: int = 100) -> list[dict]:
    limit = max(1, min(limit, 500))
    with db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM audit_logs WHERE tenant_id=? ORDER BY id DESC LIMIT ?", (tenant_id, limit)
        )]
