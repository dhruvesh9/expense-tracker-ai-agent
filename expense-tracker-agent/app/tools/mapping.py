from app.tools import expense_tools

TOOL_HANDLERS = {
    "list_expenses": expense_tools.list_expenses,
    "create_expense": expense_tools.create_expense,
    "update_expense": expense_tools.update_expense,
    "delete_expense": expense_tools.delete_expense,
    "get_summary": expense_tools.get_summary,
}
