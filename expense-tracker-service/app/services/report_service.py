from calendar import monthrange
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.errors import InvalidReferenceError
from app.money import from_minor_units
from app.repositories.expense_repository import ExpenseFilters, ExpenseRepository
from app.repositories.user_repository import UserFilters, UserRepository

WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _average(total_minor: int, count: int) -> Decimal:
    """Mean amount, rounded to 2 decimals (only used for display statistics).

    ``count`` is never 0 here: a group only exists if it has at least one expense.
    """
    return (Decimal(total_minor) / count / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _base(row) -> dict:
    """Fields shared by every grouped row."""
    return {
        "currency": row.currency,
        "total": from_minor_units(row.total_minor),
        "count": row.count,
    }


class ReportService:
    """Read-only analytics. Every total is grouped by currency."""

    def __init__(self, session: Session) -> None:
        self.expenses = ExpenseRepository(session)
        self.users = UserRepository(session)

    def summary(self, filters: ExpenseFilters) -> dict:
        rows = self.expenses.totals_by_currency(filters)
        return {
            "total_count": sum(r.count for r in rows),
            "by_currency": [
                {
                    **_base(r),
                    "users": r.users,
                    "average": _average(r.total_minor, r.count),
                    "minimum": from_minor_units(r.min_minor),
                    "maximum": from_minor_units(r.max_minor),
                }
                for r in rows
            ],
        }

    def by_category(self, filters: ExpenseFilters) -> dict:
        rows = self.expenses.totals_by_category(filters)
        return {"items": [{"category": r.category, **_base(r)} for r in rows]}

    def by_month(self, filters: ExpenseFilters) -> dict:
        rows = self.expenses.totals_by_month(filters)
        return {"items": [{"month": r.month, **_base(r)} for r in rows]}

    def by_category_month(self, filters: ExpenseFilters) -> dict:
        rows = self.expenses.totals_by_category_month(filters)
        return {"items": [{"category": r.category, "month": r.month, **_base(r)} for r in rows]}

    def by_user(self, filters: ExpenseFilters, limit: int | None) -> dict:
        rows = self.expenses.totals_by_user(filters, limit)
        return {"items": [{"user_id": r.user_id, "name": r.name, **_base(r)} for r in rows]}

    def by_country(self, filters: ExpenseFilters) -> dict:
        rows = self.expenses.totals_by_country(filters)
        return {"items": [{"country": r.country, **_base(r)} for r in rows]}

    def by_weekday(self, filters: ExpenseFilters) -> dict:
        items = []
        for r in self.expenses.totals_by_weekday(filters):
            weekday = (int(r.weekday) + 6) % 7  # SQLite: 0=Sunday -> ISO-style 0=Monday
            items.append({"weekday": weekday, "name": WEEKDAY_NAMES[weekday], **_base(r)})
        items.sort(key=lambda item: (item["currency"], item["weekday"]))
        return {"items": items}

    def by_day(self, filters: ExpenseFilters) -> dict:
        rows = self.expenses.totals_by_day(filters)
        return {"items": [{"day": r.expense_date, **_base(r)} for r in rows]}

    def by_merchant(self, filters: ExpenseFilters) -> dict:
        rows = self.expenses.totals_by_merchant(filters)
        return {"items": [{"merchant": r.merchant, **_base(r)} for r in rows]}

    def by_payment_method(self, filters: ExpenseFilters) -> dict:
        rows = self.expenses.totals_by_payment_method(filters)
        return {"items": [{"payment_method": r.payment_method, **_base(r)} for r in rows]}

    def active_users(self, filters: ExpenseFilters) -> dict:
        rows = self.expenses.active_users_by_month(filters)
        return {
            "items": [
                {"month": r.month, "active_users": r.active_users, "expenses": r.expenses}
                for r in rows
            ]
        }

    def user_growth(self, filters: UserFilters) -> dict:
        rows = self.users.signups_by_month(filters)
        running = 0
        items = []
        for r in rows:
            running += r.new_users
            items.append({"month": r.month, "new_users": r.new_users, "total_users": running})
        return {"items": items}

    def budgets(
        self, filters: UserFilters, month: str | None, status: str | None, limit: int
    ) -> dict:
        """Budget vs actual for one calendar month (default: the current UTC month)."""
        if month is None:
            today = datetime.now(UTC).date()
            month = f"{today.year:04d}-{today.month:02d}"
        try:
            year, mon = (int(part) for part in month.split("-"))
            first = date(year, mon, 1)
        except ValueError as exc:
            raise InvalidReferenceError("month must look like YYYY-MM") from exc
        last = date(year, mon, monthrange(year, mon)[1])

        items = []
        rows, counts = self.users.budget_usage(filters, first, last, status, limit)
        for r in rows:
            percent = float(Decimal(r.spent_minor) * 100 / r.budget_minor)
            items.append(
                {
                    "user_id": r.user_id,
                    "name": r.name,
                    "currency": r.currency,
                    "budget": from_minor_units(r.budget_minor),
                    "spent": from_minor_units(r.spent_minor),
                    "remaining": from_minor_units(r.budget_minor - r.spent_minor),
                    "percent_used": round(percent, 1),
                    "status": "over" if percent > 100 else "near" if percent >= 80 else "ok",
                }
            )
        return {
            "month": month,
            "counts": {
                "total": counts.total,
                "over": counts.over,
                "near": counts.near,
                "ok": counts.total - counts.over - counts.near,
            },
            "items": items,
        }
