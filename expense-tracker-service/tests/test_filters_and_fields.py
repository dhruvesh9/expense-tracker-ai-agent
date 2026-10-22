"""Standard filters (id, name, created/updated ranges...) and ?fields= on GET endpoints."""

from datetime import date, timedelta

import pytest

TODAY = date.today()
YESTERDAY = (TODAY - timedelta(days=1)).isoformat()
TOMORROW = (TODAY + timedelta(days=1)).isoformat()


@pytest.fixture
def people(client):
    """Three users; only Asha owns an expense."""
    users = [
        client.post("/api/v1/users", json={"name": n}).json() for n in ("Asha", "Ashok", "Bina")
    ]
    client.post(
        "/api/v1/expenses",
        json={
            "user_id": users[0]["id"],
            "amount": "10",
            "expense_date": "2026-01-01",
            "category": "food",
        },
    )
    return users


def names(response):
    return [item["name"] for item in response.json()["items"]]


# ---- users ---------------------------------------------------------------------------


def test_users_filter_by_one_or_many_ids(client, people):
    a, b, c = (u["id"] for u in people)
    assert names(client.get(f"/api/v1/users?id={b}")) == ["Ashok"]
    assert names(client.get(f"/api/v1/users?id={a}&id={c}")) == ["Asha", "Bina"]
    assert client.get("/api/v1/users?id=999").json()["total"] == 0


def test_users_name_contains_is_case_insensitive(client, people):
    assert names(client.get("/api/v1/users?name=ASH")) == ["Asha", "Ashok"]
    assert client.get("/api/v1/users?name=%25").json()["total"] == 0  # % is literal


def test_users_created_and_updated_ranges(client, people):
    assert client.get(f"/api/v1/users?created_from={TODAY}&created_to={TODAY}").json()["total"] == 3
    assert client.get(f"/api/v1/users?created_to={YESTERDAY}").json()["total"] == 0
    assert client.get(f"/api/v1/users?updated_from={TOMORROW}").json()["total"] == 0
    assert (
        client.get(f"/api/v1/users?created_from={TOMORROW}&created_to={YESTERDAY}").status_code
        == 422
    )


def test_users_has_expenses(client, people):
    assert names(client.get("/api/v1/users?has_expenses=true")) == ["Asha"]
    assert names(client.get("/api/v1/users?has_expenses=false")) == ["Ashok", "Bina"]


def test_users_sorting_and_combined_filters(client, people):
    assert names(client.get("/api/v1/users?sort=-name")) == ["Bina", "Ashok", "Asha"]
    assert names(client.get("/api/v1/users?name=ash&has_expenses=false")) == ["Ashok"]
    assert client.get("/api/v1/users?sort=bogus").status_code == 422


def test_users_fields_selection(client, people):
    data = client.get("/api/v1/users?fields=id,name&page_size=1").json()
    assert data["items"] == [{"id": people[0]["id"], "name": "Asha"}]
    assert data["total"] == 3 and data["pages"] == 3  # envelope is unchanged
    assert client.get(f"/api/v1/users/{people[0]['id']}?fields=name").json() == {"name": "Asha"}


def test_unknown_fields_rejected(client, people):
    response = client.get("/api/v1/users?fields=id,password")
    assert response.status_code == 422
    assert "password" in response.json()["error"]["message"]


# ---- expenses ------------------------------------------------------------------------


def test_expenses_filter_by_id_and_user_name_and_created_range(client, people):
    other = client.post(
        "/api/v1/expenses",
        json={"user_id": people[1]["id"], "amount": "20", "expense_date": "2026-02-02"},
    ).json()
    ids = [e["id"] for e in client.get("/api/v1/expenses?sort=id").json()["items"]]
    assert len(ids) == 2

    assert client.get(f"/api/v1/expenses?id={other['id']}").json()["total"] == 1
    assert client.get(f"/api/v1/expenses?id={ids[0]}&id={ids[1]}").json()["total"] == 2
    assert client.get("/api/v1/expenses?user_name=ashok").json()["total"] == 1
    assert client.get("/api/v1/expenses?user_name=ash").json()["total"] == 2
    assert client.get(f"/api/v1/expenses?created_from={TODAY}").json()["total"] == 2
    assert client.get(f"/api/v1/expenses?created_to={YESTERDAY}").json()["total"] == 0
    assert client.get(f"/api/v1/expenses?updated_from={TOMORROW}").json()["total"] == 0


def test_reports_accept_the_same_new_filters(client, people):
    data = client.get("/api/v1/reports/summary?user_name=asha").json()
    assert data["total_count"] == 1


def test_expenses_fields_selection(client, people):
    items = client.get("/api/v1/expenses?fields=id,amount,category").json()["items"]
    assert items == [{"id": items[0]["id"], "amount": "10.00", "category": "food"}]
    one = client.get(f"/api/v1/expenses/{items[0]['id']}?fields=description").json()
    assert one == {"description": None}
    assert client.get("/api/v1/expenses?fields=amount_minor").status_code == 422


# ---- categories ----------------------------------------------------------------------


def test_categories_filter_sort_and_fields(client, people):
    for cat in ("food", "food", "fuel"):
        client.post(
            "/api/v1/expenses",
            json={
                "user_id": people[0]["id"],
                "amount": "5",
                "expense_date": "2026-01-02",
                "category": cat,
            },
        )
    assert [c["category"] for c in client.get("/api/v1/categories?q=fu").json()] == ["fuel"]
    assert client.get("/api/v1/categories?sort=-count").json()[0] == {
        "category": "food",
        "count": 3,
    }
    assert client.get("/api/v1/categories?fields=category&sort=-category").json() == [
        {"category": "fuel"},
        {"category": "food"},
    ]


# ---- country / budget (user profile) and merchant / payment / recurring (expenses) ----------


@pytest.fixture
def market(client):
    """Asha (IN, INR, budget) and Bina (US, USD, no budget), one expense each."""
    out = {}
    specs = [
        ("Asha", "IN", "INR", "5000", "100", "Swiggy", "digital_wallet", False),
        ("Bina", "US", "USD", None, "50", "Netflix", "credit_card", True),
    ]
    for name, country, cur, budget, amount, merchant, method, recurring in specs:
        body = {"name": name, "country": country, "default_currency": cur}
        if budget:
            body["monthly_budget"] = budget
        user = client.post("/api/v1/users", json=body).json()
        client.post(
            "/api/v1/expenses",
            json={
                "user_id": user["id"],
                "amount": amount,
                "currency": cur,
                "expense_date": "2026-01-01",
                "merchant": merchant,
                "payment_method": method,
                "is_recurring": recurring,
            },
        )
        out[name] = user
    return out


def test_users_filter_by_country_budget_currency(client, market):
    assert names(client.get("/api/v1/users?country=us")) == ["Bina"]
    assert names(client.get("/api/v1/users?has_budget=true")) == ["Asha"]
    assert names(client.get("/api/v1/users?has_budget=false")) == ["Bina"]
    assert names(client.get("/api/v1/users?default_currency=usd")) == ["Bina"]
    assert client.get("/api/v1/users?country=USA").status_code == 422


def test_expense_filters_merchant_payment_recurring_and_owner_country(client, market):
    assert client.get("/api/v1/expenses?merchant=swig").json()["total"] == 1
    assert client.get("/api/v1/expenses?payment_method=credit_card").json()["total"] == 1
    assert client.get("/api/v1/expenses?is_recurring=true").json()["total"] == 1
    assert client.get("/api/v1/expenses?is_recurring=false").json()["total"] == 1
    assert client.get("/api/v1/expenses?country=IN").json()["items"][0]["amount"] == "100.00"
    assert client.get("/api/v1/expenses?payment_method=bitcoin").status_code == 422
    summary = client.get("/api/v1/reports/summary?country=US").json()
    assert summary["by_currency"][0]["total"] == "50.00"


def test_expense_new_fields_validation_and_patch(client, market):
    uid = market["Asha"]["id"]
    base = {"user_id": uid, "amount": "9", "expense_date": "2026-02-01"}
    assert (
        client.post("/api/v1/expenses", json={**base, "payment_method": "bitcoin"}).status_code
        == 422
    )
    created = client.post(
        "/api/v1/expenses", json={**base, "merchant": "  Uber ", "payment_method": "cash"}
    ).json()
    assert (created["merchant"], created["payment_method"], created["is_recurring"]) == (
        "Uber",
        "cash",
        False,
    )
    url = f"/api/v1/expenses/{created['id']}"
    patched = client.patch(url, json={"is_recurring": True, "merchant": None}).json()
    assert patched["is_recurring"] is True and patched["merchant"] is None
    assert patched["payment_method"] == "cash" and patched["amount"] == "9.00"
    assert client.patch(url, json={"is_recurring": None}).status_code == 422


def test_reports_by_country_merchant_payment_method(client, market):
    countries = client.get("/api/v1/reports/by-country").json()["items"]
    assert [(c["country"], c["currency"], c["count"]) for c in countries] == [
        ("IN", "INR", 1),
        ("US", "USD", 1),
    ]
    merchants = client.get("/api/v1/reports/by-merchant?currency=INR").json()["items"]
    assert [(m["merchant"], m["total"]) for m in merchants] == [("Swiggy", "100.00")]
    methods = client.get("/api/v1/reports/by-payment-method").json()["items"]
    assert {m["payment_method"] for m in methods} == {"digital_wallet", "credit_card"}


def test_budget_report_status_and_month_validation(client):
    user = client.post(
        "/api/v1/users",
        json={"name": "Budgeter", "monthly_budget": "1000", "default_currency": "INR"},
    ).json()
    client.post("/api/v1/users", json={"name": "No budget"})
    for amount, cur in [("700", "INR"), ("200", "INR"), ("5000", "USD")]:  # USD must not count
        client.post(
            "/api/v1/expenses",
            json={
                "user_id": user["id"],
                "amount": amount,
                "currency": cur,
                "expense_date": "2026-03-10",
            },
        )
    client.post(  # different month must not count
        "/api/v1/expenses",
        json={"user_id": user["id"], "amount": "999", "expense_date": "2026-04-01"},
    )
    data = client.get("/api/v1/reports/budgets?month=2026-03").json()
    assert data["month"] == "2026-03"
    [item] = data["items"]  # only users with a budget
    assert (item["spent"], item["remaining"], item["percent_used"], item["status"]) == (
        "900.00",
        "100.00",
        90.0,
        "near",
    )

    client.post(
        "/api/v1/expenses",
        json={"user_id": user["id"], "amount": "300", "expense_date": "2026-03-20"},
    )
    assert (
        client.get("/api/v1/reports/budgets?month=2026-03").json()["items"][0]["status"] == "over"
    )
    assert client.get("/api/v1/reports/budgets?month=2026-02").json()["items"][0]["status"] == "ok"
    assert client.get("/api/v1/reports/budgets?month=2026-13").status_code == 422


def test_user_growth_and_active_users(client, market):
    growth = client.get("/api/v1/reports/user-growth").json()["items"]
    assert len(growth) == 1 and growth[0]["new_users"] == 2 and growth[0]["total_users"] == 2
    assert client.get("/api/v1/reports/user-growth?country=IN").json()["items"][0]["new_users"] == 1
    active = client.get("/api/v1/reports/active-users").json()["items"]
    assert active == [{"month": "2026-01", "active_users": 2, "expenses": 2}]


# ---- scale helpers: several user ids, capped leaderboards, summarised budgets ------------


@pytest.fixture
def crowd(client):
    """Five users with a budget of 100 each, spending 10, 85, 120, 50 and 0."""
    users = []
    for i, spent in enumerate([10, 85, 120, 50, 0], start=1):
        user = client.post(
            "/api/v1/users", json={"name": f"User {i}", "monthly_budget": "100"}
        ).json()
        users.append(user)
        if spent:
            client.post(
                "/api/v1/expenses",
                json={"user_id": user["id"], "amount": str(spent), "expense_date": "2026-05-10"},
            )
    return users


def test_expenses_and_reports_accept_several_user_ids(client, crowd):
    a, b = crowd[0]["id"], crowd[1]["id"]
    assert client.get(f"/api/v1/expenses?user_id={a}&user_id={b}").json()["total"] == 2
    summary = client.get(f"/api/v1/reports/summary?user_id={a}&user_id={b}").json()
    assert summary["by_currency"][0]["total"] == "95.00"


def test_by_user_limit_returns_top_n(client, crowd):
    items = client.get("/api/v1/reports/by-user?limit=2").json()["items"]
    assert [i["name"] for i in items] == ["User 3", "User 2"]  # 120 then 85
    assert len(client.get("/api/v1/reports/by-user").json()["items"]) == 4  # no limit: all spenders


def test_budget_counts_status_filter_and_limit(client, crowd):
    data = client.get("/api/v1/reports/budgets?month=2026-05").json()
    assert data["counts"] == {"total": 5, "ok": 3, "near": 1, "over": 1}
    assert [i["name"] for i in data["items"]][:2] == ["User 3", "User 2"]  # worst first

    over = client.get("/api/v1/reports/budgets?month=2026-05&status=over").json()
    assert [i["name"] for i in over["items"]] == ["User 3"]
    assert over["counts"]["total"] == 5  # counts always describe everyone

    ok = client.get("/api/v1/reports/budgets?month=2026-05&status=ok&limit=2").json()
    assert [i["name"] for i in ok["items"]] == [
        "User 4",
        "User 1",
    ]  # 50% then 10%; User 5 cut by limit
    assert client.get("/api/v1/reports/budgets?month=2026-05&status=bogus").status_code == 422
