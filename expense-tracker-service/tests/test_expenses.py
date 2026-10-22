from datetime import date, timedelta


def test_create_and_get_expense(client, user):
    response = client.post(
        "/api/v1/expenses",
        json={
            "user_id": user["id"],
            "amount": "250",
            "description": "  Lunch ",
            "category": " Food ",
            "currency": "inr",
            "expense_date": "2026-01-10",
        },
    )
    assert response.status_code == 201
    expense = response.json()
    assert expense["amount"] == "250.00"  # exact decimal string, always 2 places
    assert expense["category"] == "food"  # normalised
    assert expense["currency"] == "INR"
    assert expense["description"] == "Lunch"
    assert client.get(f"/api/v1/expenses/{expense['id']}").json() == expense


def test_currency_defaults_to_inr(client, make_expense):
    assert make_expense()["currency"] == "INR"


def test_expense_date_is_separate_from_created_at(client, make_expense):
    five_days_ago = (date.today() - timedelta(days=5)).isoformat()
    expense = make_expense(expense_date=five_days_ago)
    assert expense["expense_date"] == five_days_ago
    assert expense["created_at"][:10] != expense["expense_date"]  # record created "today"


def test_unknown_user_rejected(client):
    response = client.post(
        "/api/v1/expenses", json={"user_id": 42, "amount": "5", "expense_date": "2026-01-01"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_reference"


def test_money_precision_is_exact(client, make_expense):
    # 0.1 + 0.2 != 0.3 with floats; with exact decimals it does.
    make_expense(amount="0.10")
    make_expense(amount="0.20")
    summary = client.get("/api/v1/reports/summary").json()
    assert summary["by_currency"][0]["total"] == "0.30"


def test_more_than_two_decimals_is_rejected_not_rounded(client, user):
    response = client.post(
        "/api/v1/expenses",
        json={"user_id": user["id"], "amount": "10.005", "expense_date": "2026-01-01"},
    )
    assert response.status_code == 422


def test_invalid_inputs(client, user):
    base = {"user_id": user["id"], "amount": "5", "expense_date": "2026-01-01"}
    for bad in (
        {"amount": "0"},
        {"amount": "-3"},
        {"amount": "abc"},
        {"currency": "RUPEES"},
        {"expense_date": "2026-13-45"},
        {"expense_date": "yesterday"},
        {"user_id": 0},
    ):
        assert client.post("/api/v1/expenses", json={**base, **bad}).status_code == 422, bad


def test_malformed_json_is_422(client):
    response = client.post(
        "/api/v1/expenses", content="{not json", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422


def test_partial_update_changes_only_sent_fields(client, make_expense):
    expense = make_expense(amount="75.50", description="Taxi", category="travel")
    response = client.patch(f"/api/v1/expenses/{expense['id']}", json={"description": "Cab"})
    updated = response.json()
    assert updated["description"] == "Cab"
    assert updated["amount"] == "75.50"
    assert updated["expense_date"] == expense["expense_date"]
    assert updated["category"] == "travel"
    assert updated["updated_at"] >= expense["updated_at"]
    assert updated["created_at"] == expense["created_at"]


def test_patch_can_clear_nullable_but_not_required_fields(client, make_expense):
    expense = make_expense(category="food")
    url = f"/api/v1/expenses/{expense['id']}"
    assert client.patch(url, json={"category": None}).json()["category"] is None
    assert client.patch(url, json={"amount": None}).status_code == 422
    assert client.patch(url, json={"expense_date": None}).status_code == 422


def test_update_amount_and_missing_expense(client, make_expense):
    expense = make_expense()
    assert (
        client.patch(f"/api/v1/expenses/{expense['id']}", json={"amount": "9.99"}).json()["amount"]
        == "9.99"
    )
    assert client.patch("/api/v1/expenses/999", json={"amount": "1"}).status_code == 404


def test_delete_expense(client, make_expense):
    expense = make_expense()
    assert client.delete(f"/api/v1/expenses/{expense['id']}").status_code == 204
    assert client.get(f"/api/v1/expenses/{expense['id']}").status_code == 404
    assert client.delete(f"/api/v1/expenses/{expense['id']}").status_code == 404


def test_database_foreign_key_is_enforced(client, user):
    """Even bypassing the service layer, the DB itself refuses orphan expenses."""
    import pytest
    from sqlalchemy.exc import IntegrityError

    from app.database import get_db
    from app.main import app
    from app.models import Expense

    session = next(app.dependency_overrides[get_db]())
    session.add(Expense(user_id=999, amount_minor=100, expense_date=date.today()))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()
