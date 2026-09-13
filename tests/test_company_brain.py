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
