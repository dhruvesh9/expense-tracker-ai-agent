"""Shared pytest fixtures.

A *fixture* is a function pytest runs to prepare something a test needs; a test
requests it simply by naming it as a parameter. Fixtures here give every test
its own empty in-memory database, so tests can't affect each other or the
development database (test isolation).
"""

import os

# Must happen before importing the app so the real dev DB path is never used.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["REPORT_CACHE_SECONDS"] = "0"  # tests must always see fresh data

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.database import build_engine, get_db
from app.main import app
from app.models import Base


@pytest.fixture
def client():
    """HTTP client that talks to the app in-process (no real server needed)."""
    engine = build_engine("sqlite://")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    # Dependency override: wherever the app asks for get_db, hand out the test DB instead.
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()  # undo, so later tests start clean
    engine.dispose()


@pytest.fixture
def user(client):
    return client.post("/api/v1/users", json={"name": "Asha"}).json()


@pytest.fixture
def make_expense(client, user):
    """Fixture returning a *factory function*: tests call it with only the fields they care about."""

    def _make(**overrides):
        body = {"user_id": user["id"], "amount": "100.00", "expense_date": "2026-01-15"}
        body.update(overrides)
        response = client.post("/api/v1/expenses", json=body)
        assert response.status_code == 201, response.text
        return response.json()

    return _make
