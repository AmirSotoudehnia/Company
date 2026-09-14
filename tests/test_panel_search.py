import os
from pathlib import Path

os.environ["AGENT_COMPANY_DB"] = str(Path(__file__).parent / "test_panel_search.db")

from app.db import init_db
from app.runtime_config import get_search, set_search


def setup_function():
    path = Path(os.environ["AGENT_COMPANY_DB"])
    if path.exists():
        path.unlink()
    init_db()


def test_search_configuration_persists():
    assert get_search()["query"] == "software developer"
    saved = set_search("flutter developer", 250)
    assert saved == {
        "query": "flutter developer",
        "limit": 100,
        "mode": "job_ads",
        "source": "arbetsformedlingen_jobtech",
    }
    assert get_search() == saved


def test_control_panel_search_endpoint(monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main

    monkeypatch.setattr(main, "search_now", lambda query, limit, mode: {
        "query": query, "limit": limit, "mode": mode, "source": "arbetsformedlingen_jobtech",
        "found": 7, "new": 3,
    })
    with TestClient(main.app) as client:
        config = client.get("/control/search")
        assert config.status_code == 200
        result = client.post("/control/search/start", json={
            "query": "Flutter developer", "limit": 20, "mode": "job_ads",
        })
    assert result.status_code == 200
    assert result.json()["new"] == 3


def test_local_business_result_is_verification_lead():
    from app.integrations.local_businesses import LocalBusinessConnector

    item = LocalBusinessConnector._convert({
        "type": "node", "id": 42,
        "tags": {"name": "Example AB", "office": "company"},
    }, "Växjö")
    assert item.source == "openstreetmap_missing_website"
    assert "Verify independently" in item.brief
    assert item.source_url.endswith("/node/42")


def test_search_run_and_results_are_visible(monkeypatch):
    import app.company_worker as worker
    from app.opportunity_discovery import DiscoveredOpportunity
    from app.control_panel import dashboard_snapshot

    class FakeConnector:
        def search(self, query, limit):
            return [DiscoveredOpportunity(
                title="Visible result",
                brief="A sufficiently detailed verified test opportunity",
                source="test_source",
                source_url="https://example.com/result-1",
            )]

    monkeypatch.setattr(worker, "JobTechConnector", FakeConnector)
    result = worker.search_now("developer", 5, "job_ads")
    snapshot = dashboard_snapshot()
    assert result["status"] == "completed"
    assert snapshot["search_runs"][0]["status"] == "completed"
    assert snapshot["opportunities"][0]["title"] == "Visible result"
