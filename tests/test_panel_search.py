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
        "source": "arbetsformedlingen_jobtech",
    }
    assert get_search() == saved


def test_control_panel_search_endpoint(monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main

    monkeypatch.setattr(main, "search_now", lambda query, limit: {
        "query": query, "limit": limit, "source": "arbetsformedlingen_jobtech",
        "found": 7, "new": 3,
    })
    with TestClient(main.app) as client:
        config = client.get("/control/search")
        assert config.status_code == 200
        result = client.post("/control/search/start", json={
            "query": "Flutter developer", "limit": 20,
        })
    assert result.status_code == 200
    assert result.json()["new"] == 3
