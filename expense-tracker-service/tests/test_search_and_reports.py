import pytest


@pytest.fixture
def seeded(client, user, make_expense):
    make_expense(
        amount="250.00", description="Lunch at cafe", category="food", expense_date="2026-01-05"
    )
    make_expense(
        amount="40.00", description="Bus ticket", category="travel", expense_date="2026-01-20"
    )
    make_expense(
        amount="1200.50",
        description="Groceries 100% organic",
        category="food",
        expense_date="2026-02-02",
    )
    make_expense(
        amount="30.00",
        currency="USD",
        description="Book",
        category="books",
        expense_date="2026-02-10",
    )
    return user


def ids(response):
    return [e["description"] for e in response.json()["items"]]


def test_filter_by_category_and_currency(client, seeded):
    assert len(client.get("/api/v1/expenses?category=FOOD").json()["items"]) == 2
    assert ids(client.get("/api/v1/expenses?currency=usd")) == ["Book"]


def test_keyword_search_is_case_insensitive_and_wildcards_are_literal(client, seeded):
    assert ids(client.get("/api/v1/expenses?q=LUNCH")) == ["Lunch at cafe"]
    assert ids(client.get("/api/v1/expenses?q=100%25")) == ["Groceries 100% organic"]
    assert client.get("/api/v1/expenses?q=%25").json()["total"] == 1  # "%" isn't "match all"


def test_date_range_is_inclusive(client, seeded):
    r = client.get("/api/v1/expenses?date_from=2026-01-20&date_to=2026-02-02&sort=expense_date")
    assert ids(r) == ["Bus ticket", "Groceries 100% organic"]


def test_amount_range(client, seeded):
    r = client.get("/api/v1/expenses?min_amount=40&max_amount=250&currency=INR&sort=amount")
    assert ids(r) == ["Bus ticket", "Lunch at cafe"]


def test_combined_filters(client, seeded):
    r = client.get("/api/v1/expenses?category=food&date_from=2026-02-01&min_amount=100")
    assert ids(r) == ["Groceries 100% organic"]


def test_filter_by_user(client, seeded):
    other = client.post("/api/v1/users", json={"name": "Other"}).json()
    assert client.get(f"/api/v1/expenses?user_id={other['id']}").json()["total"] == 0
    assert client.get(f"/api/v1/expenses?user_id={seeded['id']}").json()["total"] == 4


def test_sorting(client, seeded):
    assert (
        ids(client.get("/api/v1/expenses?currency=INR&sort=-amount"))[0] == "Groceries 100% organic"
    )
    assert ids(client.get("/api/v1/expenses?currency=INR&sort=amount"))[0] == "Bus ticket"
    assert ids(client.get("/api/v1/expenses"))[0] == "Book"  # default: newest expense_date first
    assert client.get("/api/v1/expenses?sort=bogus").status_code == 422


def test_pagination(client, seeded):
    p1 = client.get("/api/v1/expenses?page_size=3&sort=id").json()
    p2 = client.get("/api/v1/expenses?page_size=3&page=2&sort=id").json()
    assert (p1["total"], p1["pages"], len(p1["items"]), len(p2["items"])) == (4, 2, 3, 1)
    assert not {e["id"] for e in p1["items"]} & {e["id"] for e in p2["items"]}
    assert client.get("/api/v1/expenses?page=99").json()["items"] == []
    assert client.get("/api/v1/expenses?page_size=1000").status_code == 422


def test_invalid_filter_ranges(client, seeded):
    assert client.get("/api/v1/expenses?date_from=2026-02-01&date_to=2026-01-01").status_code == 422
    assert client.get("/api/v1/expenses?min_amount=9&max_amount=1").status_code == 422
    assert client.get("/api/v1/expenses?min_amount=1.234").status_code == 422


def test_summary_never_mixes_currencies(client, seeded):
    data = client.get("/api/v1/reports/summary").json()
    assert data["total_count"] == 4
    assert data["by_currency"] == [
        {
            "currency": "INR",
            "total": "1490.50",
            "count": 3,
            "users": 1,
            "average": "496.83",
            "minimum": "40.00",
            "maximum": "1200.50",
        },
        {
            "currency": "USD",
            "total": "30.00",
            "count": 1,
            "users": 1,
            "average": "30.00",
            "minimum": "30.00",
            "maximum": "30.00",
        },
    ]


def test_summary_with_date_range_and_user(client, seeded):
    data = client.get(
        f"/api/v1/reports/summary?user_id={seeded['id']}&date_from=2026-01-01&date_to=2026-01-31"
    ).json()
    assert data["by_currency"] == [
        {
            "currency": "INR",
            "total": "290.00",
            "count": 2,
            "users": 1,
            "average": "145.00",
            "minimum": "40.00",
            "maximum": "250.00",
        }
    ]


def test_report_by_category_and_month(client, seeded):
    cats = client.get("/api/v1/reports/by-category").json()["items"]
    assert {"category": "food", "currency": "INR", "total": "1450.50", "count": 2} in cats
    months = client.get("/api/v1/reports/by-month").json()["items"]
    assert [(m["month"], m["currency"], m["total"]) for m in months] == [
        ("2026-01", "INR", "290.00"),
        ("2026-02", "INR", "1200.50"),
        ("2026-02", "USD", "30.00"),
    ]


def test_empty_report(client):
    assert client.get("/api/v1/reports/summary").json() == {"total_count": 0, "by_currency": []}


def test_categories_listing(client, seeded):
    cats = client.get("/api/v1/categories").json()
    assert {"category": "food", "count": 2} in cats


# ---- extra reports used by the admin console --------------------------------------------


def test_report_by_user_joins_names_and_respects_filters(client, seeded):
    second = client.post("/api/v1/users", json={"name": "Bina"}).json()
    client.post(
        "/api/v1/expenses",
        json={"user_id": second["id"], "amount": "5000", "expense_date": "2026-03-01"},
    )
    items = client.get("/api/v1/reports/by-user?currency=INR").json()["items"]
    assert [(i["name"], i["total"], i["count"]) for i in items] == [
        ("Bina", "5000.00", 1),  # biggest spender first
        ("Asha", "1490.50", 3),
    ]
    # user_name filter together with the join must not confuse the two "users" tables
    filtered = client.get("/api/v1/reports/by-user?currency=INR&user_name=bin").json()["items"]
    assert [i["name"] for i in filtered] == ["Bina"]


def test_report_by_weekday_is_monday_based(client, seeded):
    items = client.get("/api/v1/reports/by-weekday?currency=INR").json()["items"]
    # 2026-01-05 and 2026-02-02 are Mondays; 2026-01-20 is a Tuesday
    assert [(i["weekday"], i["name"], i["total"], i["count"]) for i in items] == [
        (0, "Mon", "1450.50", 2),
        (1, "Tue", "40.00", 1),
    ]


def test_report_by_day(client, seeded):
    items = client.get("/api/v1/reports/by-day?currency=INR&date_to=2026-01-31").json()["items"]
    assert [(i["day"], i["total"]) for i in items] == [
        ("2026-01-05", "250.00"),
        ("2026-01-20", "40.00"),
    ]


def test_report_by_category_month(client, seeded):
    items = client.get("/api/v1/reports/by-category-month?currency=INR").json()["items"]
    assert [(i["month"], i["category"], i["total"]) for i in items] == [
        ("2026-01", "food", "250.00"),
        ("2026-01", "travel", "40.00"),
        ("2026-02", "food", "1200.50"),
    ]
