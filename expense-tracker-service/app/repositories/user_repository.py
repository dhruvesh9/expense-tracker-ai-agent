import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import ColumnElement, and_, case, exists, func, select
from sqlalchemy.orm import Session

from app.models import Expense, User

logger = logging.getLogger(__name__)


def _like_escape(text: str) -> str:
    """Make %, _ literal inside a LIKE pattern so user input can't act as a wildcard."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def day_start(day: date) -> datetime:
    """Midnight UTC at the start of ``day`` (timestamps are stored in UTC)."""
    return datetime.combine(day, time.min, tzinfo=UTC)


def created_range_conditions(
    column, start: date | None, end: date | None
) -> list[ColumnElement[bool]]:
    """Inclusive whole-day range on a timestamp column: [start 00:00, end+1day 00:00)."""
    conditions = []
    if start is not None:
        conditions.append(column >= day_start(start))
    if end is not None:
        conditions.append(column < day_start(end + timedelta(days=1)))
    return conditions


@dataclass
class UserFilters:
    ids: list[int] | None = None
    name: str | None = None  # case-insensitive "contains"
    created_from: date | None = None
    created_to: date | None = None
    updated_from: date | None = None
    updated_to: date | None = None
    has_expenses: bool | None = None
    has_budget: bool | None = None
    country: str | None = None  # ISO code, upper-case
    city: str | None = None  # exact match, case-insensitive
    default_currency: str | None = None


def build_user_conditions(filters: UserFilters) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if filters.ids:
        conditions.append(User.id.in_(filters.ids))
    if filters.name:
        conditions.append(User.name.ilike(f"%{_like_escape(filters.name)}%", escape="\\"))
    if filters.country:
        conditions.append(User.country == filters.country)
    if filters.city:
        conditions.append(func.lower(User.city) == filters.city.lower())
    if filters.default_currency:
        conditions.append(User.default_currency == filters.default_currency)
    if filters.has_budget is not None:
        conditions.append(
            User.monthly_budget_minor.is_not(None)
            if filters.has_budget
            else User.monthly_budget_minor.is_(None)
        )
    conditions += created_range_conditions(
        User.created_at, filters.created_from, filters.created_to
    )
    conditions += created_range_conditions(
        User.updated_at, filters.updated_from, filters.updated_to
    )
    if filters.has_expenses is not None:
        has_any = exists().where(Expense.user_id == User.id)
        conditions.append(has_any if filters.has_expenses else ~has_any)
    return conditions


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, **fields) -> User:
        logger.debug("component=user_repository action=insert_user")
        user = User(**fields)
        self.session.add(user)
        self.session.flush()  # sends INSERT now so user.id is populated (not yet committed)
        return user

    def get(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def list(
        self, filters: UserFilters, sort_column: str, descending: bool, page: int, page_size: int
    ) -> tuple[list[User], int]:
        conditions = build_user_conditions(filters)
        total = self.session.scalar(select(func.count()).select_from(User).where(*conditions)) or 0
        column = getattr(User, sort_column)
        order = column.desc() if descending else column.asc()
        stmt = (
            select(User)
            .where(*conditions)
            .order_by(order, User.id.desc() if descending else User.id.asc())  # stable ties
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        return list(self.session.scalars(stmt).all()), total

    def delete(self, user: User) -> None:
        self.session.delete(user)
        self.session.flush()

    def count_expenses(self, user_id: int) -> int:
        stmt = select(func.count()).select_from(Expense).where(Expense.user_id == user_id)
        return self.session.scalar(stmt) or 0

    def delete_expenses(self, user_id: int) -> None:
        for expense in self.session.scalars(select(Expense).where(Expense.user_id == user_id)):
            self.session.delete(expense)
        self.session.flush()

    # ---- reporting queries ----------------------------------------------------------

    def signups_by_month(self, filters: UserFilters):
        """New users per calendar month (UTC), by created_at."""
        month = func.strftime("%Y-%m", User.created_at).label("month")  # SQLite function
        stmt = (
            select(month, func.count().label("new_users"))
            .where(*build_user_conditions(filters))
            .group_by(month)
            .order_by(month)
        )
        return self.session.execute(stmt).all()

    def budget_usage(
        self,
        filters: UserFilters,
        first_day: date,
        last_day: date,
        status: str | None = None,
        limit: int = 50,
    ):
        """Budget vs actual for users with a budget: spend in their default currency in the month.

        Returns ``(rows, counts)``: rows are the worst offenders first (optionally only one
        status, at most ``limit``); counts are for *all* matching users, so a dashboard can
        show "3,412 over budget" without downloading 3,412 rows.
        LEFT OUTER JOIN keeps users who spent nothing (spent = 0).
        """
        spent = func.coalesce(func.sum(Expense.amount_minor), 0).label("spent_minor")
        usage = (
            select(
                User.id.label("user_id"),
                User.name.label("name"),
                User.default_currency.label("currency"),
                User.monthly_budget_minor.label("budget_minor"),
                spent,
            )
            .outerjoin(
                Expense,
                and_(
                    Expense.user_id == User.id,
                    Expense.currency == User.default_currency,
                    Expense.expense_date >= first_day,
                    Expense.expense_date <= last_day,
                ),
            )
            .where(User.monthly_budget_minor.is_not(None), *build_user_conditions(filters))
            .group_by(User.id)
            .subquery()
        )
        percent = usage.c.spent_minor * 100.0 / usage.c.budget_minor
        is_over, is_near = percent > 100, and_(percent >= 80, percent <= 100)

        counts_row = self.session.execute(
            select(
                func.count().label("total"),
                func.coalesce(func.sum(case((is_over, 1), else_=0)), 0).label("over"),
                func.coalesce(func.sum(case((is_near, 1), else_=0)), 0).label("near"),
            ).select_from(usage)
        ).one()

        stmt = select(usage)
        if status == "over":
            stmt = stmt.where(is_over)
        elif status == "near":
            stmt = stmt.where(is_near)
        elif status == "ok":
            stmt = stmt.where(percent < 80)
        stmt = stmt.order_by(percent.desc(), usage.c.user_id).limit(limit)
        return self.session.execute(stmt).all(), counts_row
