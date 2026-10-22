# Architecture

```
HTTP ─▶ middleware ─▶ route (app/api) ─▶ service ─▶ repository ─▶ SQLite
        (request id)   validates via      rules +     SQL only
                       Pydantic schema    commit
```

| Layer | Directory | Responsibility | Must NOT |
|---|---|---|---|
| Routes | `app/api/` | Parse HTTP input, pick status code, call a service | contain business rules or SQL |
| Schemas | `app/schemas/` | Pydantic validation/serialisation of JSON | touch the database |
| Services | `app/services/` | Business rules, existence checks, **commit/rollback** | know about HTTP |
| Repositories | `app/repositories/` | Build and run queries | decide business rules |
| Models | `app/models/` | Table definitions | validate API input |

## Decisions and why

* **SQLAlchemy 2 ORM + Alembic** – standard Python ORM with parameterised queries; Alembic gives safe, versioned schema changes.
* **Pydantic v2 schemas separate from ORM models** – API shape can evolve independently of tables; `amount` is a Decimal in the API but integer `amount_minor` in the DB.
* **Services own the transaction** – one service method = one unit of work (`session.commit()` inside). Commit isn't in a FastAPI `yield` dependency because since recent FastAPI versions that cleanup may run *after* the response is sent, so a failing commit would be invisible to the client.
* **Categories are normalised free text, not a table** – a categories table adds joins and management endpoints for little value; `GET /categories` lists those in use.
* **Delete user with expenses → 409** unless `delete_expenses=true`; the DB also has `ON DELETE RESTRICT` as a safety net.
* **One error shape** – the agent can parse every failure the same way.
* **Sync (def) routes** – SQLAlchemy sessions here are synchronous; FastAPI runs `def` routes in a thread pool, which is simple and fine for SQLite.
* **Configuration** – `app/config.py` (pydantic-settings): env vars > `.env` > defaults.
* **Not included on purpose** – auth, Docker, caching, queues.
