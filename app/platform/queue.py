from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from app.db import db


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def enqueue_job(tenant_id: int, repository_id: int, kind: str, payload: dict[str, Any], max_attempts: int = 3) -> dict:
    with db() as conn:
        repo = conn.execute("SELECT 1 FROM repositories WHERE id=? AND tenant_id=? AND enabled=1", (repository_id, tenant_id)).fetchone()
        if not repo:
            raise ValueError("Repository does not belong to tenant")
        cur = conn.execute(
            "INSERT INTO jobs(tenant_id,repository_id,kind,payload_json,max_attempts) VALUES(?,?,?,?,?)",
            (tenant_id, repository_id, kind, json.dumps(payload, ensure_ascii=False), max(1, min(max_attempts, 5))),
        )
        return dict(conn.execute("SELECT * FROM jobs WHERE id=?", (cur.lastrowid,)).fetchone())


def claim_next_job(worker_id: str, lease_seconds: int = 900) -> dict | None:
    now = datetime.now(timezone.utc)
    lease_until = _iso(now + timedelta(seconds=lease_seconds))
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """SELECT * FROM jobs
               WHERE attempts < max_attempts
                 AND available_at <= CURRENT_TIMESTAMP
                 AND (status='queued' OR (status='running' AND lease_until IS NOT NULL AND lease_until < CURRENT_TIMESTAMP))
               ORDER BY id LIMIT 1"""
        ).fetchone()
        if not row:
            return None
        job_id = int(row["id"])
        conn.execute(
            "UPDATE jobs SET status='running', attempts=attempts+1, locked_by=?, lease_until=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (worker_id, lease_until, job_id),
        )
        return dict(conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())


def complete_job(job_id: int, result: dict[str, Any]) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE jobs SET status='completed', result_json=?, lease_until=NULL, locked_by=NULL, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (json.dumps(result, ensure_ascii=False), job_id),
        )


def fail_job(job_id: int, error: str, retry_delay_seconds: int = 60) -> None:
    with db() as conn:
        row = conn.execute("SELECT attempts,max_attempts FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            return
        terminal = int(row["attempts"]) >= int(row["max_attempts"])
        status = "failed" if terminal else "queued"
        available = _iso(datetime.now(timezone.utc) + timedelta(seconds=retry_delay_seconds))
        conn.execute(
            "UPDATE jobs SET status=?, last_error=?, available_at=?, lease_until=NULL, locked_by=NULL, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, error[-8000:], available, job_id),
        )


def list_jobs(tenant_id: int, limit: int = 100) -> list[dict]:
    limit = max(1, min(limit, 500))
    with db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM jobs WHERE tenant_id=? ORDER BY id DESC LIMIT ?", (tenant_id, limit))]
