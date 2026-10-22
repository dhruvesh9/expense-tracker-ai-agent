# Mentor walkthrough: `POST /api/v1/expenses`

One real request followed in time order, from server startup to the response. Code is quoted as written in the project.

## 0. The map

```
middleware.py → api/v1/expenses.py → schemas/expense.py   (validation)
              → api/deps.py + database.py                 (dependencies)
              → services/expense_service.py               (rules + commit)
              → repositories/expense_repository.py        (SQL)
              → models/expense.py → SQLite → JSON back out
```

## 1. Before any request: the route gets registered

Python executes a module top to bottom when it is imported. Starting the server imports `app.main`, which imports the route modules. That import is what registers the routes.

**`app/api/v1/expenses.py`**
```python
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import ExpenseFiltersDep, ExpenseServiceDep, PageParam, PageSizeParam
from app.schemas.common import Page, make_page
from app.schemas.expense import ExpenseCreate, ExpenseRead, ExpenseUpdate

router = APIRouter(prefix="/expenses", tags=["expenses"])
```

**Imports**
- `from X import a, b` loads module `X` once and binds the names `a` and `b` in this file.
- `from app.schemas.expense import ExpenseCreate` works because `app` is a **package**, a folder containing `__init__.py`. Python finds it because you start the server from the project root, which is on `sys.path`.
- Import order is standard library, then third-party, then our own code. Ruff's `I` rule enforces it.

**`router = APIRouter(prefix="/expenses", ...)`**
- A mini-application: a collection of routes sharing a path prefix.
- `tags` only groups them in Swagger UI.
- `main.py` mounts it with `app.include_router(api_router, prefix="/api/v1")`. Final path: `/api/v1` + `/expenses` + `""` = `/api/v1/expenses`.

```python
@router.post("", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
def create_expense(payload: ExpenseCreate, service: ExpenseServiceDep, response: Response):
    expense = service.create_expense(payload)
    response.headers["Location"] = f"/api/v1/expenses/{expense.id}"
    return expense
```

### The decorator

`@router.post(...)` is a function that receives your function and registers it. It is equivalent to:

```python
def create_expense(...): ...
create_expense = router.post("", ...)(create_expense)
```

It does not change what your function does. It records "a POST on this path calls this function" in the router's table. That happens once at import time, not per request.

- `response_model=ExpenseRead`: the return value is converted and validated through this schema; it also defines the documented response in Swagger.
- `status_code=201`: the success status code.

### The signature, the most important line

```python
def create_expense(payload: ExpenseCreate, service: ExpenseServiceDep, response: Response):
```

FastAPI inspects this signature and uses the **type hints** to decide where each argument comes from:

| Parameter | Hint | FastAPI's conclusion |
|---|---|---|
| `payload` | `ExpenseCreate` (a Pydantic model) | read it from the **JSON body** and validate it |
| `service` | `ExpenseServiceDep` (`Annotated[..., Depends(...)]`) | **call a dependency function** and pass in the result |
| `response` | `Response` | pass in the response object so I can add headers |

You never call `create_expense` yourself. FastAPI calls it with ready-made arguments. This is **inversion of control**: you declare what you need and the framework supplies it.

- Python itself ignores type hints at runtime. FastAPI and Pydantic read them and act on them, which is why a hint here changes behaviour.
- The route is `def`, not `async def`, because the database driver blocks. FastAPI runs plain `def` routes in a worker thread so they don't freeze the event loop.

## 2. The request arrives: middleware runs first

```
curl -X POST /api/v1/expenses -d '{"user_id":1,"amount":"250","expense_date":"2026-10-18",...}'
```

uvicorn receives the bytes and calls the ASGI app (`app.main:app`). Before routing, the request passes through our middleware, registered in `create_app()` with `app.middleware("http")(request_context_middleware)`.

**`app/middleware.py`**
```python
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    token = request_id_var.set(request_id)
    start = time.perf_counter()
    logger.info("request_started method=%s path=%s", request.method, request.url.path)

    try:
        response = await call_next(request)
    except Exception:
        logger.exception("unhandled_exception")
        response = JSONResponse(status_code=500, content={...})
```

- **`async def` and `await`:** the middleware is a coroutine. `await call_next(request)` means "run everything else (routing, validation, your route) and give me the response, and let other requests run while I wait."
- **`headers.get(...) or uuid...`:** `or` returns the first truthy value. If the caller sent `X-Request-ID`, it is used. Otherwise a new 12-character hex ID is made.
- **ContextVar:** `request_id_var` is like a global variable whose value is separate for each concurrent request. `.set()` returns a token so `.reset(token)` can restore the old value later. This is how a log line deep in a repository prints the request ID without anyone passing it down.
- **`try/except` around `call_next`:** the safety net, covered in section 11.

## 3. Routing, then Pydantic validation

FastAPI matches `POST /api/v1/expenses` to `create_expense` and starts building its arguments. For `payload`, it parses the JSON and constructs an `ExpenseCreate`.

**`app/schemas/expense.py`: the types**
```python
Amount = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2, examples=["250.00"])]
Currency = Annotated[str, Field(pattern=r"^[A-Za-z]{3}$", examples=["INR"])]
```

`Annotated[T, extra]` means "type `T`, plus metadata". Pydantic reads the metadata as rules:
- `gt=0`: must be greater than zero.
- `decimal_places=2`: more than 2 decimals is an **error**, not a silent rounding. That is why `"10.005"` returns 422.
- Naming these as variables (`Amount`, `Currency`) lets the create and update schemas reuse them.

```python
class ExpenseCreate(ExpenseBase):
    user_id: int = Field(gt=0)
    amount: Amount
    currency: Currency = "INR"
    description: str | None = Field(default=None, max_length=500, examples=["Lunch"])
    category: str | None = Field(default=None, max_length=50, examples=["food"])
    expense_date: date = Field(description="Day the money was spent (YYYY-MM-DD)")
```

- `amount: Amount` has no default, so it is **required**. Missing means 422.
- `currency: Currency = "INR"` is optional and defaults to `"INR"`.
- `str | None` means a string or `None`. With `default=None` it is optional and nullable.
- `expense_date: date` is Python's `datetime.date`. Pydantic parses `"2026-10-18"` into a real `date` object. `"2026-13-45"` and `"yesterday"` fail.
- The JSON `"250"` becomes `Decimal("250")`, an exact type. Pydantic builds the `Decimal` from the text and never goes through a float.

**The validators, which run after the type checks**
```python
class ExpenseBase(BaseModel):
    @field_validator("currency", check_fields=False)
    @classmethod
    def _upper_currency(cls, value): return value.upper() if value else value
    # _category: strip + lowercase, "" → None;  _description: strip, "" → None
```

- `@field_validator("currency")` means "run this function on that field's value after it passes its type and pattern checks". The input `"inr"` passes the regex, then becomes `"INR"`. The returned value replaces the field's value.
- `@classmethod` means the first argument is the class (`cls`), not an instance. Pydantic requires that form.
- `check_fields=False` is needed because the base class does not define a `currency` field. The fields live in the subclasses.
- Inheritance gives both `ExpenseCreate` and `ExpenseUpdate` the same cleaning rules. It is one level deep, which keeps it easy to follow.

**If validation fails:** Pydantic collects all errors and raises `RequestValidationError`. Your route never runs. `handle_validation_error` in `main.py` turns the errors into the standard `{"error": {...}}` shape with status 422. It logs only the field names, never the submitted values.

> **Note:** FastAPI resolves dependencies and validates the body in one phase, in an internal order you should not rely on. For example, `get_db` may open a session even when the body is invalid. (`docs/request-lifecycle.md` lists them as sequential steps for simplicity.) The guarantee that matters holds: your function body runs only if both succeed.

## 4. Dependency injection: where `service` comes from

**`app/api/deps.py`**
```python
DbSession = Annotated[Session, Depends(get_db)]

def get_expense_service(db: DbSession) -> ExpenseService:
    return ExpenseService(db)

ExpenseServiceDep = Annotated[ExpenseService, Depends(get_expense_service)]
```

Read it from the bottom up, which is the order FastAPI resolves it in:
1. The route needs `service: ExpenseServiceDep`, which means `Depends(get_expense_service)`.
2. `get_expense_service` needs `db: DbSession`, which means `Depends(get_db)`.
3. FastAPI calls `get_db()`, then `get_expense_service(db=<that session>)`, then `create_expense(payload=..., service=<that service>, ...)`.

Within one request, the same `get_db` result is reused, so everything shares **one session**.

Why do this instead of creating the objects inside the route?
- **Testability:** `tests/conftest.py` does `app.dependency_overrides[get_db] = override_get_db`. The route and service never know they are talking to a test database.
- **Separation:** the route does not know how sessions are made.

**`app/database.py`: `get_db`, a generator used as a resource manager**
```python
def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

`yield` makes this a **generator**. FastAPI runs it up to the `yield`, hands the session to the request, and after the request finishes it resumes the function so cleanup runs.
- If the route raised an exception, FastAPI throws it back into the generator at the `yield`. The `except` does `rollback()` and re-raises with a bare `raise`, so the error keeps propagating to the handlers.
- `finally` always runs, on success or failure, so the session always closes. It gives the same guarantee as a `with` block.

**What a Session is:** a unit of work. It holds a connection from the pool and a transaction, tracks the Python objects you add or change, and sends SQL when you `flush()` or `commit()`.

`SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)` is a factory for sessions. By default SQLAlchemy marks every object stale after a commit and reloads it on the next access. `expire_on_commit=False` turns that off, so `expense.id` and `expense.created_at` stay readable after the commit without an extra query.

## 5. The service: business rules and the transaction

**`app/services/expense_service.py`**
```python
logger = logging.getLogger(__name__)

class ExpenseService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.expenses = ExpenseRepository(session)
        self.users = UserRepository(session)

    def create_expense(self, data: ExpenseCreate) -> Expense:
        logger.debug("component=expense_service action=create_expense")
        if self.users.get(data.user_id) is None:
            raise InvalidReferenceError(f"User {data.user_id} does not exist")
        expense = Expense(
            user_id=data.user_id,
            amount_minor=to_minor_units(data.amount),
            ...
        )
        self.expenses.add(expense)
        self.session.commit()
        logger.info("expense_created expense_id=%s user_id=%s", expense.id, expense.user_id)
        return expense
```

- **`__init__`:** the constructor. `self.session = session` stores the object on the instance. The service and both repositories get the **same** session, so they are all part of one transaction.
- **`-> Expense`:** the return type. It is documentation and tool support only.
- **`data: ExpenseCreate`:** by now this is a validated, cleaned object. The service trusts it and does not re-check types.
- **User check:** `self.users.get(...)` is `session.get(User, id)`, which returns `None` if the row is missing. The database foreign key would also reject a bad `user_id`, but only with an ugly `IntegrityError`. Checking first lets us return a clear 422.
- **`raise InvalidReferenceError(...)`:** an exception stops this function immediately and unwinds up the call stack. Nothing has been written yet, so there is nothing to undo.
- **`Expense(...)`:** builds an ORM object in memory. **No SQL runs yet.**
- **`to_minor_units(data.amount)`** (`app/money.py`): `Decimal("250")` × 100 gives 25000, checked to be a whole number and returned as an `int`. This is the boundary between the API's decimal and the database's integer.
- **Why the service commits:** one service method is one business operation, so it is one transaction. Success means commit. An exception means nothing is committed.
- **`logging.getLogger(__name__)`:** `__name__` is the module's dotted path, `app.services.expense_service`. That name appears in each log line.
- **Lazy formatting:** `logger.info("... %s ...", value)` builds the string only if that level is enabled. That is why log calls use `%s` instead of f-strings.

## 6. The repository: where SQL happens

**`app/repositories/expense_repository.py`**
```python
def add(self, expense: Expense) -> Expense:
    logger.debug("component=expense_repository action=insert_expense")
    self.session.add(expense)
    self.session.flush()
    return expense
```

- **`session.add(expense)`:** marks the object as pending, so the session now tracks it. Still no SQL.
- **`session.flush()`:** sends `INSERT INTO expenses (...) VALUES (?, ?, ...)` to SQLite **inside the open transaction**. Values are bound parameters, not pasted into the SQL string, which is what prevents SQL injection.
- After the flush, SQLAlchemy knows the new `id` and sets `expense.id`. It also fills `created_at` and `updated_at` through the `default=utcnow` on the model.
- **`flush` vs `commit`:** a flush sends SQL, but other connections cannot see the row and it can still be rolled back. Only the commit in the service makes it permanent.

**`app/models/expense.py`: the model it writes to**
```python
id: Mapped[int] = mapped_column(primary_key=True)
user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
amount_minor: Mapped[int] = mapped_column(Integer)
...
@property
def amount(self) -> Decimal:
    return from_minor_units(self.amount_minor)
```

- `Mapped[int]` is the Python type of the attribute. `mapped_column(...)` is the column definition. Together they say "this attribute is a column".
- `Mapped[str | None]` becomes a nullable column.
- `@property` turns a method into something you access like an attribute: `expense.amount` with no parentheses. The response schema uses it to turn `25000` back into `Decimal("250.00")`.
- `TimestampMixin` supplies `created_at` and `updated_at`. A mixin is a small class meant only to be inherited for the fields it adds.

## 7. The commit

Back in the service, `self.session.commit()` ends the transaction: SQLite writes the row durably and the connection returns to the pool. If the commit fails, for example from a locked database, SQLAlchemy raises an exception and the failure flow in section 11 applies.

The database also has its own safety net, set up in `build_engine`:
- `PRAGMA foreign_keys=ON` on every connection, because SQLite ignores foreign keys by default.
- `CHECK (amount_minor > 0)`.

Even if the Python checks had a bug, the database would refuse bad data.

## 8. Serialization: ORM object to JSON

Back in the route:
```python
response.headers["Location"] = f"/api/v1/expenses/{expense.id}"
return expense
```

- `response: Response` is the injected response object. Setting `headers` on it adds a header to the real response. A `Location` header after a create is a REST convention.
- `return expense` returns an **ORM object**, not a dict.
- FastAPI then applies `response_model=ExpenseRead`. In `ExpenseRead`, `model_config = ConfigDict(from_attributes=True)` lets Pydantic read **attributes** (`expense.user_id`) instead of dictionary keys. This is the bridge between the ORM and the API, and it is why the two class families exist.
- It builds `ExpenseRead`, then serializes it to JSON. `Decimal` becomes the string `"250.00"` (exact), `date` becomes `"2026-10-18"`, and `datetime` becomes ISO text ending in `Z`.
- Fields not declared in `ExpenseRead` cannot leak out, so the response schema acts as a filter.
- The 201 status from the decorator is applied.

## 9. Back through the middleware

```python
duration_ms = (time.perf_counter() - start) * 1000
response.headers["X-Request-ID"] = request_id
level = logging.WARNING if response.status_code >= 400 else logging.INFO
logger.log(level, "request_completed status=%s duration_ms=%.1f", ...)
request_id_var.reset(token)
return response
```

The middleware adds the request-ID header, logs completion at INFO (or WARNING for 4xx and 5xx), and resets the ContextVar. Then uvicorn sends the bytes to the client.

## 10. How every log line gets its `request_id`

Real server output from a run:
```
19:15:21,478 INFO  request_id=b03ab908a481 app.request | request_started method=POST path=/api/v1/expenses
19:15:21,494 INFO  request_id=b03ab908a481 app.services.expense_service | expense_created expense_id=1 user_id=1
19:15:21,495 INFO  request_id=b03ab908a481 app.request | request_completed status=201 duration_ms=16.8
```

The mechanism is in `app/logging_config.py`:
1. `logging.getLogger("app.services.expense_service")` creates a logger with no handler of its own, so each record **propagates up** to the root logger.
2. `configure_logging()` runs at startup from `lifespan`. It gave the root logger one handler with `RequestIdFilter`, which runs `record.request_id = request_id_var.get()` on every record.
3. The formatter string `request_id=%(request_id)s` prints that attribute.
4. The level check (`LOG_LEVEL`) is what hides the DEBUG lines at INFO. At `DEBUG` you also see the `component=... action=...` lines from the service and repository.

## 11. The failure paths

**A. Bad body (`"amount": "1.234"`)**
- Middleware, then Pydantic fails, then `handle_validation_error`, then a 422 response.
- The middleware logs `request_completed status=422` at WARNING.
- The service and repository are never reached.

**B. Unknown user (`user_id: 99`)**
- Validation passes and the service raises `InvalidReferenceError`.
- The exception travels up through the route and into `get_db`'s `except`, which rolls back and re-raises.
- `handle_app_error` in `main.py` reads `exc.status_code` (422) and `exc.code` (`invalid_reference`) and builds the JSON.
- FastAPI converts the exception into a response before it reaches our middleware, so the middleware sees an ordinary 422 and logs it as a WARNING.

**C. A genuine bug (say a `ZeroDivisionError` in a service)**
- No handler is registered for a bare `Exception`, so it propagates up to `await call_next(request)`.
- Our `except Exception` there logs `unhandled_exception` with the full stack trace (`logger.exception` includes it automatically).
- It then builds a generic 500 response with `code: internal_error` and the `request_id`.
- The client gets no internals, and you find the stack trace in the logs by that ID.
- This path is designed but not covered by an automated test yet.

**D. The commit itself fails**
- Same flow as C, except `get_db` rolls back first, so the transaction is discarded.

## Experiments to try

1. Run `LOG_LEVEL=DEBUG` and POST an expense; match each log line to a section above.
2. Send `"amount": "1.234"` and read `error.details`.
3. Send `"user_id": 99` and compare the status code with case A.
4. Run with `SQL_ECHO=true` and watch the `INSERT` appear at the `flush()` and the `COMMIT` after it.
5. Open `/docs` and see how the schema in section 3 becomes the documented request body.
6. In a Python shell: `from app.schemas.expense import ExpenseCreate; ExpenseCreate(user_id=1, amount="250", currency="inr", expense_date="2026-10-18")` and look at the cleaned result.
