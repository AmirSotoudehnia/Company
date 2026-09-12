import os
import tempfile

fd, path = tempfile.mkstemp(prefix="sales_pipeline_", suffix=".db")
os.close(fd)
os.environ["AGENT_COMPANY_DB"] = path

from app.agents.opportunity import OpportunityAgent
from app.db import init_db
from app.sales_pipeline import SalesPipeline


def test_opportunity_agent_qualifies_capability_match():
    result = OpportunityAgent().assess("API automation", "Build a Python API with GitHub automation", 1000)
    assert result.decision == "qualified"
    assert result.score >= 60


def test_pipeline_drafts_proposal_and_requires_human_approval():
    init_db()
    item = SalesPipeline().create("AI API", "Build a Python AI API automation service", "manual", budget=1000)
    assert item["status"] == "awaiting_human_approval"
    assert item["proposal_text"]
    assert len(item["approvals"]) == 1
    assert item["approvals"][0]["status"] == "pending"

def test_human_can_approve_proposal_without_auto_sending():
    init_db()
    pipeline = SalesPipeline()
    item = pipeline.create("Web automation", "Build a Python web automation API", budget=500)
    approval_id = item["approvals"][0]["id"]
    decided = pipeline.decide(item["id"], approval_id, True, "Approved for outreach")
    assert decided["status"] == "proposal_approved"
    assert decided["approvals"][0]["status"] == "approved"


def test_risky_opportunity_requires_review_and_has_no_sales_approval():
    init_db()
    item = SalesPipeline().create(
        "Urgent access", "Need urgent production access credentials and unlimited revisions"
    )
    assert item["status"] == "not_ready"
    assert item["approvals"] == []
