def test_user_crud(client):
    created = client.post("/api/v1/users", json={"name": "  Ravi  "})
    assert created.status_code == 201
    user = created.json()
    assert user["name"] == "Ravi"  # whitespace trimmed by the schema validator
    assert created.headers["Location"] == f"/api/v1/users/{user['id']}"

    assert client.get(f"/api/v1/users/{user['id']}").json()["name"] == "Ravi"

    updated = client.patch(f"/api/v1/users/{user['id']}", json={"name": "Ravi K"})
    assert updated.json()["name"] == "Ravi K"

    assert client.delete(f"/api/v1/users/{user['id']}").status_code == 204
    assert client.get(f"/api/v1/users/{user['id']}").status_code == 404


def test_list_users_paginates_and_searches(client):
    for name in ["Asha", "Ashok", "Bina"]:
        client.post("/api/v1/users", json={"name": name})
    page = client.get("/api/v1/users", params={"page_size": 2}).json()
    assert (page["total"], page["pages"], len(page["items"])) == (3, 2, 2)
    found = client.get("/api/v1/users", params={"name": "ash"}).json()
    assert [u["name"] for u in found["items"]] == ["Asha", "Ashok"]


def test_blank_and_missing_name_rejected(client):
    assert client.post("/api/v1/users", json={"name": "   "}).status_code == 422
    response = client.post("/api/v1/users", json={})
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["location"] == "body.name"


def test_missing_user_returns_404_error_shape(client):
    response = client.get("/api/v1/users/999")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert error["request_id"]


def test_delete_user_with_expenses_conflicts_unless_forced(client, user, make_expense):
    make_expense()
    response = client.delete(f"/api/v1/users/{user['id']}")
    assert response.status_code == 409
    assert response.json()["error"]["details"] == {"expense_count": 1}

    assert client.delete(f"/api/v1/users/{user['id']}?delete_expenses=true").status_code == 204
    assert client.get("/api/v1/expenses").json()["total"] == 0


def test_profile_fields_are_normalised_and_patchable(client):
    created = client.post(
        "/api/v1/users",
        json={
            "name": "Meera",
            "country": "gb",
            "default_currency": "gbp",
            "monthly_budget": "1500",
        },
    ).json()
    assert created["country"] == "GB"
    assert created["default_currency"] == "GBP"
    assert created["monthly_budget"] == "1500.00"

    # PATCH only what changes; budget and country can be cleared with null
    patched = client.patch(
        f"/api/v1/users/{created['id']}", json={"monthly_budget": None, "country": None}
    ).json()
    assert (patched["name"], patched["default_currency"]) == ("Meera", "GBP")
    assert patched["monthly_budget"] is None and patched["country"] is None

    url = f"/api/v1/users/{created['id']}"
    assert client.patch(url, json={"name": None}).status_code == 422
    assert client.patch(url, json={"default_currency": None}).status_code == 422
    assert client.post("/api/v1/users", json={"name": "X", "country": "GBR"}).status_code == 422
    assert (
        client.post("/api/v1/users", json={"name": "X", "monthly_budget": "-5"}).status_code == 422
    )
    assert (
        client.post("/api/v1/users", json={"name": "X", "monthly_budget": "1.234"}).status_code
        == 422
    )


def test_profile_defaults(client):
    created = client.post("/api/v1/users", json={"name": "Solo"}).json()
    assert created["country"] is None
    assert created["default_currency"] == "INR"
    assert created["monthly_budget"] is None
