import hashlib
import hmac
import json
import uuid

from app.core.settings import settings
from app.db import init_db
from app.integrations.webhooks import WebhookError, process_github_webhook, verify_signature
from app.platform.policy import RepositoryPolicy
from app.platform.tenancy import create_tenant, register_installation, register_repository


def test_webhook_signature_and_deduplication():
    init_db()
    original = settings.github_webhook_secret
    settings.github_webhook_secret = "test-secret"
    try:
        body = b'{"hello":"world"}'
        signature = "sha256=" + hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
        verify_signature(body, signature)
        try:
            verify_signature(body, "sha256=bad")
            assert False, "invalid signature should fail"
        except WebhookError:
            pass
    finally:
        settings.github_webhook_secret = original


def test_issue_label_enqueues_once():
    init_db()
    suffix = uuid.uuid4().hex[:8]
    tenant, _ = create_tenant(f"Webhook {suffix}")
    installation_id = 800000000 + int(suffix[:5], 16)
    register_installation(tenant["id"], installation_id, f"acct-{suffix}")
    repo = register_repository(
        tenant["id"], installation_id, "owner", f"repo-{suffix}",
        policy_json=RepositoryPolicy(required_label="agent:run").to_json(),
    )
    payload = {
        "action": "labeled",
        "repository": {"full_name": repo["full_name"]},
        "issue": {"number": 42, "labels": [{"name": "agent:run"}]},
    }
    body = json.dumps(payload).encode()
    delivery = f"delivery-{suffix}"
    first = process_github_webhook(delivery, "issues", body)
    second = process_github_webhook(delivery, "issues", body)
    assert first["job_id"] is not None
    assert second == {"duplicate": True}
