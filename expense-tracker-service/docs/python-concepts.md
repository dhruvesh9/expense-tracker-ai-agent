# Python concepts used here

* **Packages/modules** – every `.py` file is a module; a folder with `__init__.py` is a package (`app`, `app.models`). `from app.errors import NotFoundError` imports across them.
* **Type hints** – `def get(self, user_id: int) -> User | None` documents types; FastAPI/Pydantic *use* them to validate and build OpenAPI docs. `X | None` means optional.
* **Classes** – services/repositories keep a `session` in `__init__` and expose methods. `@dataclass` (`ExpenseFilters`) generates the boilerplate for plain data holders.
* **Decorators** – `@router.post(...)` registers a function as a route; `@field_validator` hooks validation; `@property` (`Expense.amount`) makes a method look like an attribute; `@lru_cache` memoises.
* **Dependency injection** – `Depends(get_db)` / `Annotated[..., Depends(...)]` (`app/api/deps.py`): FastAPI builds what a route needs; tests substitute fakes.
* **Generators & context managers** – `get_db` uses `yield`: code before runs at setup, `finally` after runs at cleanup. `with TestClient(app)` and `with engine.connect()` use context managers to guarantee cleanup. `lifespan` in `main.py` is an `asynccontextmanager`.
* **Exceptions** – we define our own (`app/errors.py`) and raise them in services; handlers translate them into HTTP responses. `raise ... from exc` keeps the original cause.
* **Pydantic models** – classes whose annotated attributes are validated on creation; `model_dump(exclude_unset=True)` gives only provided fields (PATCH).
* **SQLAlchemy ORM** – `Mapped[...]`/`mapped_column` describe columns; `Session` tracks changes; `flush()` sends SQL, `commit()` ends the transaction.
* **ContextVar** – per-request storage that works with concurrency (`request_id_var`).
* **async vs def** – middleware/handlers are `async def`; routes are plain `def` (run in a thread pool) because the DB driver is blocking.
* **Environment variables** – config outside code (`.env`, `config.py`).
* **Virtual environments** – `.venv` isolates this project's packages; `requirements.txt` lists them (`pip install -r`).
