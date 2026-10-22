# Expense Tracker Service

A FastAPI + SQLite backend that owns **users** and **expenses**. It has no LLM/agent code;
the separate agent project calls it over HTTP. The code is heavily commented so it also
works as a guide to professional Python backend development.

> **Security:** there is no authentication or authorization. Run it locally only. Before
> exposing it to untrusted networks you need auth, HTTPS, rate limiting and proper deployment controls.

## Getting started (Linux, Python 3.12+)

```bash
python3 -m venv .venv                 # create the virtual environment
source .venv/bin/activate             # activate it (prompt shows "(.venv)")
pip install -r requirements.txt       # install dependencies
cp .env.example .env                  # optional: all settings have defaults
alembic upgrade head                  # create/upgrade the SQLite DB (data/expense_tracker.db)
uvicorn app.main:app --reload --port 8001   # start the server
```

* Swagger UI: <http://127.0.0.1:8001/docs> · ReDoc: `/redoc` · OpenAPI JSON: `/openapi.json`
* Health: `GET /health` (liveness), `GET /ready` (checks the database)
* Tests: `pytest` · Single test: `pytest tests/test_expenses.py::test_partial_update_changes_only_sent_fields -v`
* Quality: `ruff check .` and `ruff format --check .` (fix with `ruff check --fix . && ruff format .`)
* `make help` lists all shortcuts: `make setup start start-debug migrate migration seed reset shell test lint format check` (e.g. `make migration m="add notes column"`).

### Admin console

Open **<http://127.0.0.1:8001/console/>** (also `/`): a dashboard served by this same process, calling the REST API.
Pages: **Overview** (KPIs, trends, insights), **Expenses** (filter / sort / create / edit / delete / CSV export),
**Users** (budgets, per-user spend, CRUD), **Analytics** (growth, monthly active users, budget health, merchants,
payment methods, fixed vs flexible spend, category trends, spending calendar), and **Present** (a full-screen deck
built from live data; arrow keys to move, `F` fullscreen, `Esc` exit). Light/dark theme, design tokens in
`app/console/css/tokens.css`. Charts use a vendored copy of Chart.js (no CDN needed). No authentication: local use only.

### Database migrations (Alembic)

```bash
alembic upgrade head                                  # apply all migrations (also creates the DB)
alembic revision --autogenerate -m "add notes column" # after editing a model in app/models
alembic upgrade head                                  # review the generated file first, then apply
alembic downgrade -1                                  # undo the last migration
alembic current                                       # which version the DB is at
sqlite3 data/expense_tracker.db ".tables" "SELECT * FROM expenses LIMIT 5;"   # inspect data
```

Dummy data: `make seed` loads random dummy data from `scripts/seed.sql`: 10 users with ~110 expenses in total, each with a spending personality (regenerate a fresh random set with `make seed-generate ARGS="--users 10 --max-expenses 12"`). `make reset` wipes the dev DB, migrates and reseeds.

### Load-test data (10,000 daily active users)

`make seed-load` replaces the data with a simulated large user base: **25,000 users and ~1.9 million
expenses over 180 days (about 5-6k daily actives)**, ~30-40 s, ~0.6 GB. Names are unique ("First Last"), each user has a city. Tune it with
`make seed-load ARGS="--users 20000 --days 90 --dau 4000"`; `--seed N` makes it reproducible. It writes
straight into SQLite (indexes are dropped during the load and rebuilt after). Go back to the small
friendly dataset with `make reset`.

Performance notes at this size (measured): list endpoints and filters answer in milliseconds;
report aggregates over millions of rows take 0.2-2 s. Migration `0003` adds *covering indexes* that cut
reports 2-6x. The next step, if you outgrow this, is a pre-aggregated daily rollup table (or PostgreSQL).
The console never loads "all users": it searches and pages, and asks the API for top-N lists and counts.

## Project layout

```
app/
  main.py            builds the FastAPI app, registers error handlers + middleware
  config.py          Settings loaded from env vars / .env
  database.py        engine, Session factory, get_db dependency
  logging_config.py  log format + request_id ContextVar
  middleware.py      request id, start/finish logs, last-resort 500 handler
  errors.py          AppError, NotFoundError, ConflictError, InvalidReferenceError
  money.py           Decimal <-> integer minor units
  models/            SQLAlchemy ORM models (tables)
  schemas/           Pydantic models (API request/response JSON)
  repositories/      all SQL queries
  services/          business rules + transactions (commit)
  api/               routes (api/v1/*), shared dependencies (deps.py), health
migrations/          Alembic migration scripts
tests/               pytest suite (in-memory DB per test)
docs/                learning docs      examples/   sample HTTP client
```

Why this layering? Each layer has one job, so you can change one without touching the rest:
routes handle HTTP only → services hold rules and own the transaction → repositories hold SQL →
models map tables. It is the smallest structure that keeps SQL out of routes and HTTP out of business code.

See `docs/` for details: [architecture](docs/architecture.md), [request lifecycle](docs/request-lifecycle.md),
[database](docs/database.md), [logging](docs/logging.md), [testing](docs/testing.md),
[python concepts](docs/python-concepts.md), [API integration](docs/api-integration.md).

## API summary (prefix `/api/v1`)

| Method & path | Purpose |
|---|---|
| `POST /users`, `GET /users`, `GET/PATCH/DELETE /users/{id}` | User CRUD (`DELETE ?delete_expenses=true` cascades) |
| `POST /expenses`, `GET /expenses`, `GET/PATCH/DELETE /expenses/{id}` | Expense CRUD + search |
| `GET /categories` | Categories in use, with counts |
| `GET /reports/summary` | Total, count, average, min, max per currency |
| `GET /reports/by-category`, `/by-month`, `/by-category-month`, `/by-user`, `/by-weekday`, `/by-day`, `/by-country`, `/by-merchant`, `/by-payment-method` | Grouped totals (always per currency); accept the same filters as `GET /expenses` |
| `GET /reports/active-users` | Monthly active users (distinct users with an expense that month); expense filters |
| `GET /reports/user-growth` | New and cumulative users per signup month; user filters |
| `GET /reports/budgets?month=YYYY-MM` | Budget vs actual per user (`ok` < 80%, `near` 80-100%, `over` > 100%); user filters |
| `GET /health`, `GET /ready` (root, unversioned) | Liveness / readiness |

**User fields:** `name`, `country` (ISO code), `default_currency`, `monthly_budget` (optional), timestamps.
**Expense fields:** amount, currency, expense_date, category, description, `merchant`, `payment_method`
(`cash|credit_card|debit_card|bank_transfer|digital_wallet|other`), `is_recurring`, timestamps.

**Filters (all combine with AND)**

| Endpoint | Query parameters |
|---|---|
| `GET /users` (and `/reports/user-growth`, `/reports/budgets`) | `id` (repeatable), `name` (contains), `country`, `default_currency`, `has_budget`, `has_expenses`, `created_from/to`, `updated_from/to`, `sort=[-]id|name|created_at|updated_at`, `page`, `page_size`, `fields` |
| `GET /expenses` and expense `/reports/*` | `id` (repeatable), `user_id`, `user_name`, `country` (owner's), `category`, `currency`, `q` (description), `merchant` (contains), `payment_method`, `is_recurring`, `date_from/date_to`, `min_amount/max_amount`, `created_from/to`, `updated_from/to` |
| `GET /expenses` only | `sort=[-]expense_date|amount|created_at|id`, `page`, `page_size` (<=100), `fields` |
| `GET /categories` | `user_id`, `q`, `sort=[-]category|count`, `fields` |

**`fields`**: `?fields=id,name` returns only those fields (on the list endpoints, `GET /users/{id}`, `GET /expenses/{id}` and `/categories`). Unknown names return 422. It trims the response payload only; the pagination envelope (`total`, `pages`...) stays.

Lists return `{items, total, page, page_size, pages}`.
Errors always look like `{"error": {"code", "message", "details", "request_id"}}`.

## curl examples

```bash
B=http://127.0.0.1:8001/api/v1
curl -s -X POST $B/users -H 'Content-Type: application/json' -d '{"name":"Asha"}'
curl -s -X POST $B/expenses -H 'Content-Type: application/json' \
  -d '{"user_id":1,"amount":"250.00","description":"Lunch","category":"food","expense_date":"2026-10-18"}'
curl -s $B/expenses/1
curl -s -X PATCH $B/expenses/1 -H 'Content-Type: application/json' -d '{"description":"Team lunch"}'
curl -s "$B/expenses?q=lunch&category=food&sort=-amount&page=1&page_size=10"
curl -s "$B/expenses?date_from=2026-10-01&date_to=2026-10-31&min_amount=100"
curl -s "$B/expenses?user_name=asha&fields=id,amount,expense_date&sort=-amount"
curl -s "$B/users?name=ash&has_expenses=true&fields=id,name"
curl -s "$B/users?id=1&id=2"
curl -s "$B/reports/summary?user_id=1&date_from=2026-10-01"
curl -s "$B/reports/by-category"; curl -s "$B/reports/by-month"
curl -s -X DELETE $B/expenses/1 -i
```

## Money and dates

* Amounts are exact decimals, sent/returned as strings (`"250.00"`), max 2 decimals (more → 422, never rounded), must be > 0.
  Stored as integer minor units (paise). All currencies are assumed to have 2 decimals.
* `expense_date` = when the money was spent; `created_at`/`updated_at` (UTC) = when the record changed.
* Totals are grouped per currency; currencies are never summed together.

## Logging and tracing

```bash
LOG_LEVEL=DEBUG uvicorn app.main:app --port 8001   # or set LOG_LEVEL=DEBUG in .env
SQL_ECHO=true  ...                                 # additionally print every SQL statement
```

Every line carries `request_id=...`, and the same ID is returned in the `X-Request-ID` response header
(send your own header to correlate with the agent's logs). Trace one request:

```bash
curl -si -X POST $B/expenses ... | grep -i x-request-id    # e.g. a1b2c3d4e5f6
grep a1b2c3d4e5f6 server.log                               # or: uvicorn ... 2>&1 | tee server.log
```

Bodies and submitted values are never logged. Details: [docs/logging.md](docs/logging.md).

## Debugging guide

* **422 validation_error** – read `error.details`: each item has `location` (e.g. `body.amount`), `message`, `type`.
* **404 not_found / 409 conflict / 422 invalid_reference** – business rules from `app/errors.py`.
* **500 internal_error** – copy `request_id` from the response and search the logs for the stack trace.
* **Database errors** – run with `SQL_ECHO=true`; inspect data with `sqlite3`; "no such table" means run `alembic upgrade head`.
* Common FastAPI problems: *422 on a body you thought was valid* (missing `Content-Type: application/json`,
  or wrong field types); *405* (wrong HTTP method); *404 on `/expenses/`* vs `/expenses` (use the exact path).

## SQLite limitations & PostgreSQL later

SQLite allows only one writer at a time (we set a 5s busy timeout and run a single uvicorn process).
That is fine locally but not for many concurrent writers. To move to PostgreSQL: change `DATABASE_URL`,
add the driver (`psycopg`), drop the SQLite pragma hook, replace `strftime` in
`expense_repository.totals_by_month` with `to_char`/`date_trunc`, and re-run migrations.

## Calling from another Python project

See `examples/agent_client_example.py` (uses `httpx`; shares no code or DB with this service).
