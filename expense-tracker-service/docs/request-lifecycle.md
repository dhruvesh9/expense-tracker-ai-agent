# Request lifecycle: `POST /api/v1/expenses`

1. **Request arrives** at uvicorn, which hands it to the ASGI app `app.main:app`.
2. **Middleware** `app/middleware.py::request_context_middleware` sets the `request_id` ContextVar (or reuses `X-Request-ID`) and logs `request_started`.
3. **Routing** – FastAPI matches `POST /api/v1/expenses` to `create_expense` in `app/api/v1/expenses.py`.
4. **Validation** – the body is parsed into `ExpenseCreate` (`app/schemas/expense.py`): types, `amount > 0` with ≤2 decimals, 3-letter currency, valid date; validators normalise category/currency/description. Failure → `handle_validation_error` in `main.py` → 422, and the route never runs.
5. **Dependencies** – `ExpenseServiceDep` → `get_expense_service` (`app/api/deps.py`) → needs `DbSession` → `get_db` (`app/database.py`) opens a Session. The Session is closed after the response is produced.
6. **Business logic** – `ExpenseService.create_expense` checks the user exists (else `InvalidReferenceError` → 422), converts the Decimal to minor units (`app/money.py`), builds an `Expense` ORM object.
7. **Database** – `ExpenseRepository.add` does `session.add` + `flush()` (INSERT executes inside the open transaction; `expense.id` is now known).
8. **Commit** – `session.commit()` in the service makes it permanent. If anything raised earlier, nothing is committed and `close()` rolls back.
9. **Serialisation** – the route returns the ORM object; `response_model=ExpenseRead` (with `from_attributes`) converts it to JSON (`amount` as `"250.00"`), and a `Location` header is added. Status 201.
10. **Response + logs** – middleware adds `X-Request-ID` and logs `request_completed status=201 duration_ms=...`.

Log trace at `LOG_LEVEL=DEBUG`:

```
INFO  request_id=abc123 app.request | request_started method=POST path=/api/v1/expenses
DEBUG request_id=abc123 app.services.expense_service | component=expense_service action=create_expense
DEBUG request_id=abc123 app.repositories.expense_repository | component=expense_repository action=insert_expense
INFO  request_id=abc123 app.services.expense_service | expense_created expense_id=42 user_id=1
INFO  request_id=abc123 app.request | request_completed status=201 duration_ms=18.5
```

Errors: `AppError` subclasses → handler in `main.py`; unexpected exceptions → caught in the middleware, logged with stack trace, returned as generic 500.
