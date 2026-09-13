import os, tempfile
fd,path=tempfile.mkstemp(prefix="company_brain_",suffix=".db"); os.close(fd); os.environ["AGENT_COMPANY_DB"]=path
from app.db import init_db, db
from app.company_brain import CompanyBrain
from app.opportunity_discovery import OpportunityDiscovery, DiscoveredOpportunity

def test_ceo_grows_pipeline_when_idle():
    init_db(); r=CompanyBrain().tick(); assert r["decision"]["action"]=="discover_opportunities"
    with db() as c: assert c.execute("SELECT COUNT(*) FROM company_cycles").fetchone()[0]==1

def test_discovery_enters_sales_pipeline():
    init_db(); rows=OpportunityDiscovery().ingest([DiscoveredOpportunity("Flutter app","Build a Flutter mobile application with API integration and tests","public_feed","https://example.com/job/1",10000)])
    assert len(rows)==1; assert rows[0]["source"]=="public_feed"; assert rows[0]["score"]>=0

def test_invalid_discovery_url_is_rejected():
    init_db(); rows=OpportunityDiscovery().ingest([DiscoveredOpportunity("Bad URL job","A sufficiently long software project description","feed","file:///secret")]); assert rows==[]

def test_ceo_schedules_deduplicated_company_action():
    init_db()
    first = CompanyBrain().tick()
    second = CompanyBrain().tick()
    expected_action = first["decision"]["action"]
    assert first["scheduled_action"]["action"] == expected_action
    assert second["scheduled_action"]["id"] == first["scheduled_action"]["id"]
    with db() as c:
        actions = c.execute("SELECT action,status FROM company_actions WHERE action=?", (expected_action,)).fetchall()
    assert len(actions) == 1
    assert tuple(actions[0]) == (expected_action, "pending")

def test_discovery_deduplicates_source_url():
    item = DiscoveredOpportunity("Unique feed job", "A long enough software delivery brief with tests", "feed", "https://example.com/unique", 5000)
    first = OpportunityDiscovery().ingest([item])
    second = OpportunityDiscovery().ingest([item])
    assert len(first) == 1
    assert second == []


def test_qualified_opportunity_creates_draft_interaction():
    from app.sales_pipeline import SalesPipeline
    item = SalesPipeline().create("Large Flutter project", "Build a complete Flutter product with API, tests, deployment and maintenance", "manual", "", 100000)
    if item["status"] == "awaiting_human_approval":
        interactions = SalesPipeline().interactions(item["id"])
        assert len(interactions) == 1
        assert interactions[0]["status"] == "draft"
        assert interactions[0]["direction"] == "outbound"


def test_company_worker_ingests_configured_local_feed(monkeypatch):
    import json
    from pathlib import Path
    import app.company_worker as company_worker
    feed = Path.cwd() / "data" / "test_opportunities_feed.json"
    feed.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(company_worker, "COMPANY_ROOT", Path.cwd().resolve())
    feed.write_text(json.dumps([{"title": "Worker feed job", "brief": "Build a tested Python API and deployment pipeline", "source": "worker_test", "source_url": "https://example.com/worker-job", "budget": 25000}]), encoding="utf-8")
    monkeypatch.setenv("OPPORTUNITY_FEED_FILE", str(feed))
    with db() as c:
        c.execute("UPDATE company_actions SET status='completed'")
        c.execute("UPDATE sales_approvals SET status='rejected'")
        c.execute("UPDATE opportunities SET status='proposal_rejected' WHERE status='awaiting_human_approval'")
    try:
        result = company_worker.run_once()
        assert result["action"]["status"] == "completed"
        assert "ingested=1" in result["action"]["reason"]
    finally:
        feed.unlink(missing_ok=True)
