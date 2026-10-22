from app import backend_client


def list_expenses(user_id: int, category=None, date_from=None, date_to=None,
                  merchant=None, search=None, limit: int = 20):
    return backend_client.list_expenses(
        user_id=user_id,
        category=category,
        date_from=date_from,
        date_to=date_to,
        merchant=merchant,
        q=search,
        sort="-expense_date",
        page_size=min(limit, 50)
    )


def create_expense(user_id: int, amount: str, expense_date: str, currency=None,
                   description=None, category=None, merchant=None,
                   payment_method=None, is_recurring: bool = False):
    payload = {
        "user_id": user_id,
        "amount": amount,
        "expense_date": expense_date,
        "currency": currency,
        "description": description,
        "category": category,
        "merchant": merchant,
        "payment_method": payment_method,
        "is_recurring": is_recurring,
    }
    # drop None values so we never send "currency": null
    payload = {k: v for k, v in payload.items() if v is not None}
    return backend_client.create_expense(payload)

# {
#   "user_id": 1,
#   "amount": 250,
#   "currency": "INR",
#   "description": "Lunch",
#   "category": "food",
#   "expense_date": "2026-10-22",
#   "merchant": "Starbucks",
#   "payment_method": "cash",
#   "is_recurring": false
# }


def _not_yours(user_id: int, expense_id: int):
    # the backend PATCH/DELETE don't check the owner, so we do: returns an error dict or None
    expense = backend_client.get_expense(expense_id)
    if "error" in expense or expense.get("user_id") != user_id:
        return {"error": {"code": "not_found", "message": f"Expense {expense_id} not found"}}
    return None


def update_expense(user_id: int, expense_id: int, amount=None, expense_date=None,
                   currency=None, description=None, category=None, merchant=None,
                   payment_method=None, is_recurring=None):
    payload = {
        "amount": amount,
        "expense_date": expense_date,
        "currency": currency,
        "description": description,
        "category": category,
        "merchant": merchant,
        "payment_method": payment_method,
        "is_recurring": is_recurring,
    }
    # only send the fields the user wants to change
    payload = {k: v for k, v in payload.items() if v is not None}
    return _not_yours(user_id, expense_id) or backend_client.update_expense(expense_id, payload)


def delete_expense(user_id: int, expense_id: int):
    return _not_yours(user_id, expense_id) or backend_client.delete_expense(expense_id)


def get_summary(user_id: int, date_from=None, date_to=None, category=None, by_category: bool = False):
    filters = {
        "user_id": user_id,
        "date_from": date_from,
        "date_to": date_to,
        "category": category,
    }
    if by_category:
        return backend_client.get_by_category(**filters)
    return backend_client.get_summary(**filters)
