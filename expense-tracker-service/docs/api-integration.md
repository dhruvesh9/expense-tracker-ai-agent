# Consuming the API from another service

* Base URL `http://127.0.0.1:8001/api/v1`; interactive schema at `/docs`, machine-readable at `/openapi.json` (feed this to tool generators).
* JSON in/out. Money = decimal **string** (`"250.00"`), dates `YYYY-MM-DD`, timestamps ISO-8601 UTC.
* Mapping example – "Add a 250 rupee lunch expense for yesterday": agent computes yesterday's date → `POST /expenses {"user_id":1,"amount":"250","description":"Lunch","category":"food","expense_date":"<date>"}`.
* Partial updates use `PATCH` with only changed fields; sending `null` clears `description`/`category`.
* Search: `GET /expenses?id=&user_id=&user_name=&q=&category=&currency=&date_from=&date_to=&min_amount=&max_amount=&created_from=&created_to=&sort=&page=&page_size=&fields=`. Users: `GET /users?id=&name=&created_from=&has_expenses=&sort=&fields=`. Add `fields=id,amount` to get only what you need (saves tokens); `user_name` lets an agent filter by person without looking up the id first. Use `GET /categories` to reuse existing category names.
* Reports are per currency: `/reports/summary`, `/by-category`, `/by-month` (same filters).
* Errors: `{"error":{"code","message","details","request_id"}}`. Codes: `validation_error`(422), `invalid_reference`(422), `not_found`(404), `conflict`(409), `http_error`, `internal_error`(500). Handle by `code`, not message text.
* Send `X-Request-ID` to correlate logs across services.
* Work with plain HTTP only – never share ORM models or the SQLite file. Example: `examples/agent_client_example.py`.
* Not safe for untrusted networks: no auth.

## Retail-oriented data

Expenses can carry a `merchant`, a `payment_method` and `is_recurring`; users carry `country`, `default_currency` and an optional `monthly_budget`. Useful agent calls: `GET /reports/budgets?id=<user>` ("am I within budget?"), `GET /reports/by-merchant?user_id=<id>` ("where do I spend most?"), `GET /expenses?is_recurring=true&user_id=<id>` ("what are my subscriptions?").
