from __future__ import annotations

import hashlib
import hmac
import json

from app.core.settings import settings
from app.db import db
from app.platform.audit import audit
from app.platform.policy import RepositoryPolicy
from app.platform.queue import enqueue_job


class WebhookError(ValueError):
    pass


def verify_signature(body: bytes, signature: str) -> None:
    secret = settings.github_webhook_secret
    if not secret:
        raise WebhookError("GITHUB_WEBHOOK_SECRET is not configured")
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature or ""):
        raise WebhookError("Invalid webhook signature")


def process_github_webhook(delivery_id: str, event: str, body: bytes) -> dict:
    payload_hash = hashlib.sha256(body).hexdigest()
    payload = json.loads(body.decode("utf-8"))
    with db() as conn:
        duplicate = conn.execute("SELECT 1 FROM webhook_deliveries WHERE delivery_id=?", (delivery_id,)).fetchone()
        if duplicate:
            return {"duplicate": True}

        repository = payload.get("repository") or {}
        full_name = repository.get("full_name", "")
        repo_row = conn.execute("SELECT * FROM repositories WHERE full_name=? AND enabled=1", (full_name,)).fetchone()
        tenant_id = int(repo_row["tenant_id"]) if repo_row else None
        conn.execute(
            "INSERT INTO webhook_deliveries(delivery_id,event,tenant_id,payload_hash) VALUES(?,?,?,?)",
            (delivery_id, event, tenant_id, payload_hash),
        )

    if not repo_row:
        return {"accepted": True, "matched_repository": False}

    repo = dict(repo_row)
    policy = RepositoryPolicy.from_json(repo.get("policy_json"))
    if event == "issues" and payload.get("action") in {"opened", "labeled", "reopened"} and policy.auto_code_enabled:
        issue = payload.get("issue") or {}
        labels = {item.get("name") for item in issue.get("labels", []) if isinstance(item, dict)}
        if policy.required_label in labels:
            job = enqueue_job(
                repo["tenant_id"], repo["id"], "code_issue",
                {"issue_number": int(issue["number"])},
                max_attempts=policy.max_attempts,
            )
            audit(repo["tenant_id"], "github-webhook", "job.enqueued", f"issue:{issue['number']}", repo["id"], {"job_id": job["id"], "delivery_id": delivery_id})
            return {"accepted": True, "job_id": job["id"]}

    return {"accepted": True, "matched_repository": True, "job_id": None}
