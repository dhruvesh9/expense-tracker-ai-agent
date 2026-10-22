def test_health_and_ready(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").json() == {"status": "ready"}


def test_request_id_header_is_returned_and_echoed(client):
    assert client.get("/health").headers["X-Request-ID"]
    response = client.get("/health", headers={"X-Request-ID": "trace-me"})
    assert response.headers["X-Request-ID"] == "trace-me"


def test_unknown_route_uses_standard_error_shape(client):
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"


def test_admin_console_is_served(client):
    page = client.get("/console/")
    assert page.status_code == 200
    assert "text/html" in page.headers["content-type"]
    assert client.get("/", follow_redirects=False).headers["location"] == "/console/"
    assert client.get("/console/js/main.js").status_code == 200
