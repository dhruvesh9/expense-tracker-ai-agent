import httpx

from app.config import get_settings

# One shared client = connections are reused (faster than a new one per call).
_client = httpx.Client(base_url=get_settings().backend_url, timeout=10)


def _call(method: str, path: str, params: dict | None = None, json: dict | None = None):
    # Drop params that are None so we don't send "?category=None".
    params = {k: v for k, v in (params or {}).items() if v is not None}
    try:
        resp = _client.request(method, path, params=params, json=json)
    except httpx.HTTPError as exc:
        return {"error": {"code": "service_unreachable", "message": str(exc)}}
    if resp.status_code == 204:  # DELETE success: no body
        return {"ok": True}
    try:
        return resp.json()
    except ValueError:
        return {"error": {"code": "bad_response", "message": f"HTTP {resp.status_code}"}}


def get_user(user_id: int):
    return _call("GET", f"/users/{user_id}")


def list_expenses(**filters):
    # filters: user_id, category, date_from, date_to, merchant, q, sort, page_size ...
    return _call("GET", "/expenses", params=filters)


def get_expense(expense_id: int):
    return _call("GET", f"/expenses/{expense_id}")


def create_expense(payload: dict):
    return _call("POST", "/expenses", json=payload)


def update_expense(expense_id: int, payload: dict):
    return _call("PATCH", f"/expenses/{expense_id}", json=payload)


def delete_expense(expense_id: int):
    return _call("DELETE", f"/expenses/{expense_id}")


def get_summary(**filters):
    # totals per currency: total, count, average, min, max
    return _call("GET", "/reports/summary", params=filters)


def get_by_category(**filters):
    return _call("GET", "/reports/by-category", params=filters)
