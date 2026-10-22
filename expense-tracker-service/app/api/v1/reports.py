from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.api.deps import ExpenseFiltersDep, ReportServiceDep, UserFiltersDep
from app.schemas.report import (
    ActiveUsers,
    BudgetReport,
    CategoryMonthlySummary,
    CategorySummary,
    CountrySummary,
    DailySummary,
    MerchantSummary,
    MonthlySummary,
    PaymentMethodSummary,
    SummaryReport,
    UserGrowth,
    UserSummary,
    WeekdaySummary,
)

router = APIRouter(prefix="/reports", tags=["reports"])
# All report endpoints accept the same filters as GET /expenses (user, dates, category...).
# Totals are always grouped by currency; pass ?currency=INR to look at one currency.


@router.get("/summary", response_model=SummaryReport)
def summary(service: ReportServiceDep, filters: ExpenseFiltersDep):
    """Total, count, average, smallest and largest expense: one entry per currency."""
    return service.summary(filters)


@router.get("/by-category", response_model=CategorySummary)
def by_category(service: ReportServiceDep, filters: ExpenseFiltersDep):
    return service.by_category(filters)


@router.get("/by-month", response_model=MonthlySummary)
def by_month(service: ReportServiceDep, filters: ExpenseFiltersDep):
    return service.by_month(filters)


@router.get("/by-category-month", response_model=CategoryMonthlySummary)
def by_category_month(service: ReportServiceDep, filters: ExpenseFiltersDep):
    """Category x month matrix (for stacked charts)."""
    return service.by_category_month(filters)


@router.get("/by-user", response_model=UserSummary)
def by_user(
    service: ReportServiceDep,
    filters: ExpenseFiltersDep,
    limit: Annotated[
        int | None, Query(ge=1, le=1000, description="Top N users per currency (default: all)")
    ] = None,
):
    """Spending per user (only users with matching expenses), biggest spenders first.
    Use `limit` for a leaderboard; with many users, also filter by `user_id` to look up a few."""
    return service.by_user(filters, limit)


@router.get("/by-country", response_model=CountrySummary)
def by_country(service: ReportServiceDep, filters: ExpenseFiltersDep):
    """Spending grouped by the owner's country (null = no country set)."""
    return service.by_country(filters)


@router.get("/by-weekday", response_model=WeekdaySummary)
def by_weekday(service: ReportServiceDep, filters: ExpenseFiltersDep):
    """Spending by day of week of the *expense date* (0 = Monday)."""
    return service.by_weekday(filters)


@router.get("/by-day", response_model=DailySummary)
def by_day(service: ReportServiceDep, filters: ExpenseFiltersDep):
    """Daily totals by expense date (for trend lines and calendar heatmaps)."""
    return service.by_day(filters)


@router.get("/by-merchant", response_model=MerchantSummary)
def by_merchant(service: ReportServiceDep, filters: ExpenseFiltersDep):
    """Where the money goes: totals per merchant (biggest first within each currency)."""
    return service.by_merchant(filters)


@router.get("/by-payment-method", response_model=PaymentMethodSummary)
def by_payment_method(service: ReportServiceDep, filters: ExpenseFiltersDep):
    """Cash vs cards vs wallets ..."""
    return service.by_payment_method(filters)


@router.get("/active-users", response_model=ActiveUsers)
def active_users(service: ReportServiceDep, filters: ExpenseFiltersDep):
    """Monthly active users: distinct users with at least one expense that month."""
    return service.active_users(filters)


@router.get("/user-growth", response_model=UserGrowth)
def user_growth(service: ReportServiceDep, filters: UserFiltersDep):
    """New and cumulative users per signup month. Takes the same filters as GET /users."""
    return service.user_growth(filters)


@router.get("/budgets", response_model=BudgetReport)
def budgets(
    service: ReportServiceDep,
    filters: UserFiltersDep,
    month: Annotated[
        str | None,
        Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM (default: current month)"),
    ] = None,
    status: Annotated[
        Literal["ok", "near", "over"] | None, Query(description="Only users with this status")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=500, description="Max rows returned (worst first)")] = 50,
):
    """Budget vs actual for users who set a monthly budget, worst first. `counts` always covers
    every matching user. Spend is counted in each user's default currency only."""
    return service.budgets(filters, month, status, limit)
