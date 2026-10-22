from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import ExpenseFiltersDep, ExpenseServiceDep, PageParam, PageSizeParam
from app.api.fields import FieldsParam, build_item, build_page, parse_fields
from app.schemas.common import Page
from app.schemas.expense import ExpenseCreate, ExpenseRead, ExpenseUpdate

router = APIRouter(prefix="/expenses", tags=["expenses"])

# "-" prefix means descending, e.g. sort=-expense_date
SortParam = Annotated[
    str,
    Query(
        pattern=r"^-?(expense_date|amount|created_at|id)$",
        description="Field to sort by; prefix with '-' for descending",
    ),
]


@router.post("", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
def create_expense(payload: ExpenseCreate, service: ExpenseServiceDep, response: Response):
    expense = service.create_expense(payload)
    response.headers["Location"] = f"/api/v1/expenses/{expense.id}"
    return expense


@router.get("", response_model=Page[ExpenseRead])
def list_expenses(
    service: ExpenseServiceDep,
    filters: ExpenseFiltersDep,
    sort: SortParam = "-expense_date",
    page: PageParam = 1,
    page_size: PageSizeParam = 20,
    fields: FieldsParam = None,
):
    """Search/filter/sort/paginate. All filters combine with AND; `fields=id,amount` trims the response."""
    selected = parse_fields(fields, ExpenseRead)
    expenses, total = service.list_expenses(filters, sort, page, page_size)
    return build_page(ExpenseRead, expenses, total, page, page_size, selected)


@router.get("/{expense_id}", response_model=ExpenseRead)
def get_expense(expense_id: int, service: ExpenseServiceDep, fields: FieldsParam = None):
    selected = parse_fields(fields, ExpenseRead)
    return build_item(ExpenseRead, service.get_expense(expense_id), selected)


@router.patch("/{expense_id}", response_model=ExpenseRead)
def update_expense(expense_id: int, payload: ExpenseUpdate, service: ExpenseServiceDep):
    """Partial update: only the fields present in the JSON body are changed."""
    return service.update_expense(expense_id, payload)


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: int, service: ExpenseServiceDep):
    service.delete_expense(expense_id)
