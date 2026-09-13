import os
import tempfile

fd, path = tempfile.mkstemp(prefix="hardening_", suffix=".db")
os.close(fd)
os.environ["AGENT_COMPANY_DB"] = path

from app.agents.repository_gates import security_findings, quality_findings
from app.agents.acceptance import AcceptanceReviewer
from app.db import init_db, db
from app.billing import create_invoice


def test_repository_gates_detect_secret_and_skip(tmp_path):
    source = 'api_key = "123456789-secret"\nimport pytest\n@pytest.mark.skip\ndef test_x(): pass'
    (tmp_path / "x.py").write_text(source)
    assert security_findings(tmp_path, ["x.py"])
    assert quality_findings(tmp_path, ["x.py"])


def test_acceptance_rejects_no_changes(tmp_path):
    assert not AcceptanceReviewer().review(tmp_path, "implement feature", []).ok


def test_invoice_creation():
    init_db()
    with db() as conn:
        opp = conn.execute("INSERT INTO opportunities(title,brief,status) VALUES('x','long enough brief','approved')").lastrowid
        customer = conn.execute("INSERT INTO customers(name) VALUES('Customer')").lastrowid
        engagement = conn.execute("INSERT INTO engagements(opportunity_id,customer_id,scope) VALUES(?,?,?)", (opp, customer, 'long enough scope')).lastrowid
    invoice = create_invoice(engagement, 1000)
    assert invoice["number"].startswith("INV-")
    assert invoice["status"] == "draft"
