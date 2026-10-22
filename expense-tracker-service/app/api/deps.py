"""FastAPI dependencies.

Dependency injection: a route declares ``service: UserServiceDep`` and FastAPI
calls the function inside ``Depends(...)`` for each request, passing the result in.
Dependencies can themselves depend on others (the Session below), and tests can
swap any of them with ``app.dependency_overrides``.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.money import to_minor_units
from app.repositories.expense_repository import ExpenseFilters
from app.repositories.user_repository import UserFilters
from app.schemas.expense import PaymentMethod
from app.services.expense_service import ExpenseService
from app.services.report_service import ReportService
from app.services.user_service import UserService

DbSession = Annotated[Session, Depends(get_db)]


def get_user_service(db: DbSession) -> UserService:
    return UserService(db)


def get_expense_service(db: DbSession) -> ExpenseService:
    return ExpenseService(db)


def get_report_service(db: DbSession) -> ReportService:
    return ReportService(db)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
ExpenseServiceDep = Annotated[ExpenseService, Depends(get_expense_service)]
ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]


def _minor(value: Decimal | None) -> int | None:
    if value is None:
        return None
    try:
        return to_minor_units(value)
    except ValueError as exc:
        raise HTTPException(422, "amount filters may have at most 2 decimal places") from exc


def _check_range(start, end, start_name: str, end_name: str) -> None:
    if start is not None and end is not None and start > end:
        raise HTTPException(422, f"{start_name} must not be after {end_name}")


IdsParam = Annotated[
    list[int] | None, Query(alias="id", description="Repeat for several: ?id=1&id=2")
]
CreatedFrom = Annotated[date | None, Query(description="Record created on/after (UTC day)")]
CreatedTo = Annotated[date | None, Query(description="Record created on/before (UTC day)")]
UpdatedFrom = Annotated[date | None, Query(description="Record updated on/after (UTC day)")]
UpdatedTo = Annotated[date | None, Query(description="Record updated on/before (UTC day)")]


PaymentMethodParam = Annotated[PaymentMethod | None, Query(description="Exact payment method")]
CountryParam = Annotated[
    str | None, Query(pattern=r"^[A-Za-z]{2}$", description="User's country (ISO code)")
]


def get_user_filters(
    ids: IdsParam = None,
    name: Annotated[str | None, Query(description="Name contains (case-insensitive)")] = None,
    created_from: CreatedFrom = None,
    created_to: CreatedTo = None,
    updated_from: UpdatedFrom = None,
    updated_to: UpdatedTo = None,
    has_expenses: Annotated[bool | None, Query(description="true/false: has any expenses")] = None,
    has_budget: Annotated[
        bool | None, Query(description="true/false: has a monthly budget")
    ] = None,
    country: CountryParam = None,
    city: Annotated[str | None, Query(description="City (exact, any case)")] = None,
    default_currency: Annotated[str | None, Query(pattern=r"^[A-Za-z]{3}$")] = None,
) -> UserFilters:
    _check_range(created_from, created_to, "created_from", "created_to")
    _check_range(updated_from, updated_to, "updated_from", "updated_to")
    return UserFilters(
        ids=ids,
        name=name.strip() if name else None,
        created_from=created_from,
        created_to=created_to,
        updated_from=updated_from,
        updated_to=updated_to,
        has_expenses=has_expenses,
        has_budget=has_budget,
        country=country.upper() if country else None,
        city=city.strip() if city else None,
        default_currency=default_currency.upper() if default_currency else None,
    )


def get_expense_filters(
    ids: IdsParam = None,
    user_ids: Annotated[
        list[int] | None,
        Query(alias="user_id", description="Repeat for several: ?user_id=1&user_id=2"),
    ] = None,
    user_name: Annotated[str | None, Query(description="Owner's name contains")] = None,
    country: CountryParam = None,
    category: Annotated[str | None, Query(description="Exact match, case-insensitive")] = None,
    currency: Annotated[str | None, Query(pattern=r"^[A-Za-z]{3}$")] = None,
    q: Annotated[str | None, Query(description="Keyword in description")] = None,
    merchant: Annotated[str | None, Query(description="Merchant contains")] = None,
    payment_method: PaymentMethodParam = None,
    is_recurring: Annotated[bool | None, Query(description="true = subscriptions/bills")] = None,
    date_from: Annotated[date | None, Query(description="Expense date from, YYYY-MM-DD")] = None,
    date_to: Annotated[date | None, Query(description="Expense date to, inclusive")] = None,
    min_amount: Annotated[Decimal | None, Query(ge=0)] = None,
    max_amount: Annotated[Decimal | None, Query(ge=0)] = None,
    created_from: CreatedFrom = None,
    created_to: CreatedTo = None,
    updated_from: UpdatedFrom = None,
    updated_to: UpdatedTo = None,
) -> ExpenseFilters:
    """Shared by the expense list and the reports so both filter identically."""
    _check_range(date_from, date_to, "date_from", "date_to")
    _check_range(created_from, created_to, "created_from", "created_to")
    _check_range(updated_from, updated_to, "updated_from", "updated_to")
    _check_range(min_amount, max_amount, "min_amount", "max_amount")
    return ExpenseFilters(
        ids=ids,
        user_ids=user_ids,
        user_name=user_name.strip() if user_name else None,
        country=country.upper() if country else None,
        category=category.strip().lower() if category else None,
        currency=currency.upper() if currency else None,
        q=q.strip() if q else None,
        merchant=merchant.strip() if merchant else None,
        payment_method=payment_method,
        is_recurring=is_recurring,
        date_from=date_from,
        date_to=date_to,
        min_amount_minor=_minor(min_amount),
        max_amount_minor=_minor(max_amount),
        created_from=created_from,
        created_to=created_to,
        updated_from=updated_from,
        updated_to=updated_to,
    )


UserFiltersDep = Annotated[UserFilters, Depends(get_user_filters)]
ExpenseFiltersDep = Annotated[ExpenseFilters, Depends(get_expense_filters)]
PageParam = Annotated[int, Query(ge=1)]
PageSizeParam = Annotated[int, Query(ge=1, le=100)]
