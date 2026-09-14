import os
from pathlib import Path

os.environ["AGENT_COMPANY_DB"] = str(Path(__file__).parent / "test_revenue_engine.db")

from app.db import db, init_db
from app.revenue_engine import RevenueEngine, classify_revenue_prompt


class FakeSearch:
    def search(self, query, limit):
        if "sellers" in query:
            return [{"title": "Supplier listing", "url": "https://supplier.example/oil",
                     "content": "Oil available", "score": 0.8}]
        if "buyers" in query:
            return [{"title": "Buyer listing", "url": "https://buyer.example/oil",
                     "content": "Oil wanted", "score": 0.7}]
        return [{"title": "SEO candidate", "url": "https://business.example",
                 "content": "Business page with contact@example.com", "score": 0.9}]


def setup_function():
    path = Path(os.environ["AGENT_COMPANY_DB"])
    if path.exists():
        path.unlink()
    init_db()


def test_trade_prompt_searches_both_sides_without_claiming_profit():
    result = RevenueEngine(FakeSearch()).search(
        "I want to buy oil and sell it for a profit", 8
    )
    assert result["kind"] == "trade_match"
    assert {item["role"] for item in result["candidates"]} == {"buyer", "seller"}
    assert all(item["expected_profit"] is None for item in result["candidates"])
    assert all(item["verification_status"] == "needs_due_diligence"
               for item in result["candidates"])


def test_service_search_never_exposes_snippet_contact_as_verified():
    result = RevenueEngine(FakeSearch()).search(
        "Find websites in Växjö that need SEO", 5
    )
    candidate = result["candidates"][0]
    assert candidate["verification_status"] == "needs_technical_audit"
    assert "email" not in candidate
    assert "phone" not in candidate


def test_unverified_candidate_cannot_enter_sales():
    result = RevenueEngine(FakeSearch()).search(
        "Find websites in Växjö that need redesign", 5
    )
    candidate = result["candidates"][0]
    try:
        RevenueEngine(FakeSearch()).promote(candidate["id"])
        assert False, "unverified candidate was promoted"
    except ValueError as exc:
        assert "fully verified" in str(exc)


def test_classifier_does_not_treat_revenue_search_as_employment():
    assert classify_revenue_prompt("find a Flutter app project").kind == "freelance_project"
    assert classify_revenue_prompt("find SEO customers").kind == "service_lead"
    assert classify_revenue_prompt("find oil buyers and sellers").kind == "trade_match"


def test_revenue_control_endpoint(monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main

    monkeypatch.setattr(main, "RevenueEngine", lambda: RevenueEngine(FakeSearch()))
    with TestClient(main.app) as client:
        response = client.post("/control/revenue/search", json={
            "objective": "find SEO customers", "limit": 5,
        })
    assert response.status_code == 200
    assert response.json()["kind"] == "service_lead"
