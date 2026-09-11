import uuid

from app.db import init_db
from app.platform.audit import audit, list_audit
from app.platform.policy import RepositoryPolicy
from app.platform.queue import claim_next_job, complete_job, enqueue_job
from app.platform.tenancy import create_tenant, register_installation, register_repository, tenant_from_api_key


def test_tenant_isolation_queue_and_audit():
    init_db()
    suffix = uuid.uuid4().hex[:8]
    tenant_a, key_a = create_tenant(f"Tenant A {suffix}")
    tenant_b, key_b = create_tenant(f"Tenant B {suffix}")
    assert tenant_from_api_key(key_a)["id"] == tenant_a["id"]
    assert tenant_from_api_key(key_b)["id"] == tenant_b["id"]

    inst_a = 900000000 + int(suffix[:5], 16)
    register_installation(tenant_a["id"], inst_a, f"acct-{suffix}")
    policy = RepositoryPolicy(max_attempts=2)
    repo = register_repository(tenant_a["id"], inst_a, "owner", f"repo-{suffix}", policy_json=policy.to_json())

    job = enqueue_job(tenant_a["id"], repo["id"], "code_issue", {"issue_number": 1}, 2)
    claimed = claim_next_job(f"worker-{suffix}")
    assert claimed is not None
    assert claimed["id"] == job["id"]
    assert claimed["tenant_id"] == tenant_a["id"]
    complete_job(job["id"], {"ok": True})

    audit(tenant_a["id"], "test", "job.completed", f"job:{job['id']}", repo["id"], {"ok": True})
    rows_a = list_audit(tenant_a["id"])
    rows_b = list_audit(tenant_b["id"])
    assert any(row["subject"] == f"job:{job['id']}" for row in rows_a)
    assert not any(row["subject"] == f"job:{job['id']}" for row in rows_b)
