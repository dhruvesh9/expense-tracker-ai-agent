TOOLS = [
    {
        "name": "list_expenses",
        "description": "List the user's expenses, newest first. Use for questions like "
                       "'what did I spend on food last week' or 'show my recent expenses'.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "lower-case category, e.g. food"},
                "date_from": {"type": "string", "description": "YYYY-MM-DD, inclusive"},
                "date_to": {"type": "string", "description": "YYYY-MM-DD, inclusive"},
                "merchant": {"type": "string"},
                "search": {"type": "string", "description": "text to look for in the description"},
                "limit": {"type": "integer", "description": "max rows, default 20, max 50"},
            },
        },
    },
    {
        "name": "create_expense",
        "description": "Create a new expense for the user. Use when the user says they spent "
                       "or paid something, e.g. 'I paid 250 for lunch at Starbucks'.",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "string",
                    "description": "Amount as a string with up to 2 decimals, e.g. \"250.00\". Must be > 0.",
                },
                "expense_date": {
                    "type": "string",
                    "description": "Date the money was spent, YYYY-MM-DD. Resolve 'today'/'yesterday' yourself.",
                },
                "currency": {
                    "type": "string",
                    "description": "3-letter code, e.g. INR. Use the user's default currency unless they say otherwise.",
                },
                "description": {"type": "string", "description": "Short note, e.g. Lunch"},
                "category": {"type": "string", "description": "Lower-case, e.g. food, transport, rent"},
                "merchant": {"type": "string", "description": "Shop or business name, e.g. Starbucks"},
                "payment_method": {
                    "type": "string",
                    "enum": ["cash", "credit_card", "debit_card", "bank_transfer", "digital_wallet", "other"],
                },
                "is_recurring": {"type": "boolean", "description": "True only if the user says it repeats"},
            },
            "required": ["amount", "expense_date"],
        },
    },
    {
        "name": "update_expense",
        "description": "Update an existing expense. Use when the user wants to correct or change "
                       "one, e.g. 'change that to 300'. Find the expense_id with list_expenses first.",
        "parameters": {
            "type": "object",
            "properties": {
                "expense_id": {"type": "integer", "description": "id of the expense to change"},
                "amount": {"type": "string", "description": "New amount as a string, e.g. \"300.00\""},
                "expense_date": {"type": "string", "description": "New date, YYYY-MM-DD"},
                "currency": {"type": "string", "description": "3-letter code, e.g. INR"},
                "description": {"type": "string"},
                "category": {"type": "string", "description": "Lower-case, e.g. food"},
                "merchant": {"type": "string"},
                "payment_method": {
                    "type": "string",
                    "enum": ["cash", "credit_card", "debit_card", "bank_transfer", "digital_wallet", "other"],
                },
                "is_recurring": {"type": "boolean"},
            },
            "required": ["expense_id"],
        },
    },
    {
        "name": "delete_expense",
        "description": "Delete an expense. Find the expense_id with list_expenses first.",
        "parameters": {
            "type": "object",
            "properties": {
                "expense_id": {"type": "integer", "description": "id of the expense to delete"},
            },
            "required": ["expense_id"],
        },
    },
    {
        "name": "get_summary",
        "description": "Get spending totals (total, count, average, min, max). Use for questions like "
                       "'how much did I spend this month'. Set by_category for a per-category breakdown.",
        "parameters": {
            "type": "object",
            "properties": {
                "date_from": {"type": "string", "description": "YYYY-MM-DD, inclusive"},
                "date_to": {"type": "string", "description": "YYYY-MM-DD, inclusive"},
                "category": {"type": "string", "description": "lower-case category, e.g. food"},
                "by_category": {"type": "boolean", "description": "True to break totals down by category"},
            },
        },
    },
]


def get_all_tools() -> list[dict]:
    return TOOLS
