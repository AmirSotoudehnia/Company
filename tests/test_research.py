import os
from pathlib import Path

os.environ["AGENT_COMPANY_DB"] = str(Path(__file__).parent / "test_research.db")

from app.db import db, init_db
from app.research import ResearchService


class FakeTavily:
    def search(self, query, limit):
        return [{"title": "Example AB", "url": "https://example.se/contact",
                 "content": "Contact hello@example.se or +46 70 123 45 67",
                 "score": 0.91}]


def setup_function():
    path = Path(os.environ["AGENT_COMPANY_DB"])
    if path.exists():
        path.unlink()
    init_db()


def test_research_mission_persists_visible_evidence():
    mission = ResearchService(FakeTavily()).run("find an example", 5)
    assert mission["status"] == "completed"
    assert mission["result_count"] == 1
    assert mission["findings"][0]["email"] == "hello@example.se"
    assert mission["findings"][0]["confidence"] == 0.91


def test_auto_router_supports_arbitrary_research(monkeypatch):
    import app.company_worker as worker
    monkeypatch.setattr(worker, "ResearchService", lambda: ResearchService(FakeTavily()))
    result = worker.search_now("compare local accounting tools", 4, "auto")
    assert result["resolved_mode"] == "general_web"
    assert result["mission_id"] > 0
    assert result["found"] == 1


def test_sales_approval_queues_automatic_research():
    from app.sales_pipeline import SalesPipeline
    pipeline = SalesPipeline()
    opportunity = pipeline.create(
        "Qualified website lead",
        "Build a Python web automation API and complete website implementation.",
        budget=1000,
    )
    assert opportunity["approvals"]
    approved = pipeline.decide(
        opportunity["id"], opportunity["approvals"][0]["id"], True
    )
    assert approved["status"] == "proposal_approved"
    with db() as conn:
        action = conn.execute(
            "SELECT * FROM company_actions WHERE action='research_opportunity'"
        ).fetchone()
    assert action is not None
    assert str(opportunity["id"]) in action["payload_json"]
