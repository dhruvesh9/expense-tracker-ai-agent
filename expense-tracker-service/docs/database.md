# Database

**users**: `id` PK, `name`, `country` (ISO code, nullable), `default_currency` (default INR),
`monthly_budget_minor` BIGINT (nullable, minor units), `created_at`, `updated_at`.
**expenses**: `id` PK, `user_id` FK→users (`ON DELETE RESTRICT`), `amount_minor` INTEGER (`CHECK > 0`),
`currency` (3 letters, default INR), `description`, `category` (lower-case), `merchant`, `payment_method`
(`CHECK` in a fixed list), `is_recurring` BOOLEAN (default false), `expense_date` DATE, `created_at`, `updated_at`.
Indexes: `(user_id, expense_date)`, `category`, `expense_date`.

Relationship: one user → many expenses (`expenses.user_id`). Deleting a user that has expenses is blocked by the service (409) and by the database.

* **Money** – integer minor units (25050 = 250.50); exact, sortable, summable. Python side uses `Decimal`.
* **Timestamps** – stored UTC; `UTCDateTime` (`app/models/base.py`) restores the timezone on read.
* **Foreign keys** – SQLite ignores them unless `PRAGMA foreign_keys=ON`, which `database.py` sets on every connection.
* **Sessions** – one per request (`get_db`); the service commits; closing without commit discards changes.

## Migrations

Models change → `alembic revision --autogenerate -m "msg"` → read the generated file in `migrations/versions/`
→ `alembic upgrade head`. `render_as_batch=True` lets Alembic alter SQLite tables (it copies the table). Never
delete the DB as a migration strategy. `alembic check` reports if models and migrations disagree.
Note: autogenerate writes our custom `UTCDateTime` type as `app.models.base.UTCDateTime` – change it to `sa.DateTime()` in the new migration (migrations must not import app code that may change).

## Migration notes

* `0002` adds the profile/expense-detail columns. Existing rows get safe defaults (`default_currency='INR'`, `is_recurring=false`).
* SQLite "batch" migrations rebuild tables; `migrations/env.py` pauses foreign-key enforcement during a migration and verifies integrity afterwards. A test round-trips upgrade/downgrade with data.
* Alembic does not autogenerate CHECK constraints: add them by hand (as in `0002`).
* `0003` adds three covering indexes (`ix_expenses_report_*`) for the report queries. A covering index contains every column a query reads, so SQLite never touches the table. Trade-off: each index costs disk (~100 MB at 3.8M rows) and slows writes slightly.

## Scale

`scripts/generate_load_data.py` (`make seed-load`) builds ~3.8M expenses for 50k users. Things that matter at this size: never return unbounded lists (the API paginates, `by-user` has `limit`, budgets return counts plus the worst N), keep filters index-friendly, and pre-aggregate if reports must be instant. SQLite handles this read-heavy workload, but concurrent writers are its limit (see the README on PostgreSQL).
