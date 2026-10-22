# Testing

Run `pytest` (`-v` verbose, `-k keyword` to select, `path::test_name` for one test).

* `tests/conftest.py` – **fixtures**: `client` (FastAPI `TestClient` calling the app in-process), `user`, `make_expense` (a factory fixture).
* **Isolation** – each test gets a brand-new in-memory SQLite DB. The `client` fixture uses **`app.dependency_overrides[get_db]`** to swap the real database for it, so the dev DB is never touched. `DATABASE_URL=sqlite://` is also set before the app is imported as a second guard.
* Files: `test_users`, `test_expenses` (validation, partial update, money precision, FK enforcement), `test_search_and_reports` (filters, sort, pagination, per-currency totals), `test_migrations` (runs real Alembic on a temp file), `test_health`.
* Tests use plain `assert`; pytest rewrites failures to show both sides. No mocking was needed because the in-memory DB is fast and realistic; use `unittest.mock` / `monkeypatch` only for external services (e.g. a future HTTP call).
