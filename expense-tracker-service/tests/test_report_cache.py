"""The report cache serves repeats quickly and is cleared by any write."""

from app import middleware
from app.config import settings


def test_report_cache_hits_and_is_cleared_by_writes(client, monkeypatch):
    monkeypatch.setattr(settings, "report_cache_seconds", 60)
    middleware._report_cache.clear()
    user = client.post("/api/v1/users", json={"name": "Cached"}).json()

    first = client.get("/api/v1/reports/summary")
    second = client.get("/api/v1/reports/summary")
    assert first.headers.get("X-Cache") is None and second.headers["X-Cache"] == "HIT"
    assert second.json() == first.json() == {"total_count": 0, "by_currency": []}

    client.post(
        "/api/v1/expenses",
        json={"user_id": user["id"], "amount": "10", "expense_date": "2026-01-01"},
    )  # a write: cache cleared, next read is fresh
    fresh = client.get("/api/v1/reports/summary")
    assert fresh.headers.get("X-Cache") is None
    assert fresh.json()["total_count"] == 1
    middleware._report_cache.clear()
