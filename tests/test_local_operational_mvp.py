import os
from pathlib import Path

os.environ["AGENT_COMPANY_DB"] = str(Path(__file__).parent / "test_local_mvp.db")

from app.company_profile import current_profile
from app.db import db, init_db
from app.outbox import decide, list_pending, queue
from app.platform.tenancy import create_tenant, issue_api_key, list_api_keys, revoke_api_key, tenant_from_api_key


def setup_function():
    path = Path(os.environ["AGENT_COMPANY_DB"])
    if path.exists():
        path.unlink()
    init_db()


def test_profile_is_safe_local_default():
    profile = current_profile()
    assert profile.deployment_mode == "local_windows"
    assert profile.communication_provider == "chatgpt_gmail"
    assert profile.legal_status == "unregistered"
    assert profile.automatic_sending is False


def test_outbox_requires_explicit_decision_and_never_marks_sent():
    with db() as conn:
        opportunity_id = conn.execute(
            "INSERT INTO opportunities(title,brief) VALUES('Lead','A sufficiently detailed brief')"
        ).lastrowid
        interaction_id = conn.execute(
            """INSERT INTO lead_interactions(opportunity_id,direction,channel,subject,body)
               VALUES(?,'outbound','gmail','Hello','Proposal')""", (opportunity_id,)
        ).lastrowid
    approval = queue(opportunity_id, interaction_id)
    assert list_pending()[0]["id"] == approval["id"]
    result = decide(approval["id"], True, "Owner reviewed")
    assert result["status"] == "approved_for_gmail_draft"
    with db() as conn:
        status = conn.execute(
            "SELECT status FROM lead_interactions WHERE id=?", (interaction_id,)
        ).fetchone()[0]
    assert status == "approved_for_gmail_draft"


def test_tenant_key_lifecycle():
    tenant, bootstrap = create_tenant("Local Company")
    issued, replacement = issue_api_key(tenant["id"], "replacement")
    assert tenant_from_api_key(replacement)["id"] == tenant["id"]
    assert all("key_hash" not in item for item in list_api_keys(tenant["id"]))
    revoke_api_key(tenant["id"], issued["id"])
    assert tenant_from_api_key(replacement) is None
    assert tenant_from_api_key(bootstrap)["id"] == tenant["id"]
