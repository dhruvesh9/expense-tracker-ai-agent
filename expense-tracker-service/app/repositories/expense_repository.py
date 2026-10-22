import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.orm import Session, aliased

from app.models import Expense, User
from app.repositories.user_repository import _like_escape, created_range_conditions

logger = logging.getLogger(__name__)


@dataclass
class ExpenseFilters:
    """Plain container for optional filters; ``None`` means "don't filter on this"."""

    ids: list[int] | None = None
    user_ids: list[int] | None = None  # one or several owners
    user_name: str | None = None  # owner's name contains (case-insensitive)
    country: str | None = None  # owner's country (ISO code)
    category: str | None = None
    currency: str | None = None
    q: str | None = None
    merchant: str | None = None  # contains, case-insensitive
    payment_method: str | None = None
    is_recurring: bool | None = None
    date_from: date | None = None
    date_to: date | None = None
    min_amount_minor: int | None = None
    max_amount_minor: int | None = None
    created_from: date | None = None  # when the record was created (not expense_date)
    created_to: date | None = None
    updated_from: date | None = None
    updated_to: date | None = None


def build_conditions(f: ExpenseFilters) -> list[ColumnElement[bool]]:
    """Turn filters into SQL conditions. They are combined with AND by the caller.

    SQLAlchemy sends values as bound parameters, never string-pasted into SQL,
    which is what prevents SQL injection.
    """
    conditions: list[ColumnElement[bool]] = []
    if f.ids:
        conditions.append(Expense.id.in_(f.ids))
    if f.user_ids:
        conditions.append(Expense.user_id.in_(f.user_ids))
    # Filters on the expense's *owner*. aliased(): a separate "copy" of users so this
    # subquery never gets mixed up with the outer query when that also joins users
    # (see totals_by_user).
    owner = aliased(User)
    owner_conditions: list[ColumnElement[bool]] = []
    if f.user_name:
        owner_conditions.append(owner.name.ilike(f"%{_like_escape(f.user_name)}%", escape="\\"))
    if f.country:
        owner_conditions.append(owner.country == f.country)
    if owner_conditions:
        conditions.append(Expense.user_id.in_(select(owner.id).where(*owner_conditions)))
    if f.category is not None:
        conditions.append(Expense.category == f.category)
    if f.currency is not None:
        conditions.append(Expense.currency == f.currency)
    if f.q:
        conditions.append(Expense.description.ilike(f"%{_like_escape(f.q)}%", escape="\\"))
    if f.merchant:
        conditions.append(Expense.merchant.ilike(f"%{_like_escape(f.merchant)}%", escape="\\"))
    if f.payment_method is not None:
        conditions.append(Expense.payment_method == f.payment_method)
    if f.is_recurring is not None:
        conditions.append(Expense.is_recurring.is_(f.is_recurring))
    if f.date_from is not None:
        conditions.append(Expense.expense_date >= f.date_from)
    if f.date_to is not None:
        conditions.append(Expense.expense_date <= f.date_to)
    if f.min_amount_minor is not None:
        conditions.append(Expense.amount_minor >= f.min_amount_minor)
    if f.max_amount_minor is not None:
        conditions.append(Expense.amount_minor <= f.max_amount_minor)
    conditions += created_range_conditions(Expense.created_at, f.created_from, f.created_to)
    conditions += created_range_conditions(Expense.updated_at, f.updated_from, f.updated_to)
    return conditions


class ExpenseRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, expense: Expense) -> Expense:
        logger.debug("component=expense_repository action=insert_expense")
        self.session.add(expense)
        self.session.flush()
        return expense

    def get(self, expense_id: int) -> Expense | None:
        return self.session.get(Expense, expense_id)

    def delete(self, expense: Expense) -> None:
        self.session.delete(expense)
        self.session.flush()

    def search(
        self, filters: ExpenseFilters, sort_column: str, descending: bool, page: int, page_size: int
    ) -> tuple[list[Expense], int]:
        logger.debug("component=expense_repository action=search_expenses")
        conditions = build_conditions(filters)
        total = (
            self.session.scalar(select(func.count()).select_from(Expense).where(*conditions)) or 0
        )
        column = getattr(Expense, "amount_minor" if sort_column == "amount" else sort_column)
        order = column.desc() if descending else column.asc()
        # Secondary sort on id makes ordering deterministic when primary values tie,
        # which keeps pagination stable.
        stmt = (
            select(Expense)
            .where(*conditions)
            .order_by(order, Expense.id.desc() if descending else Expense.id.asc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        return list(self.session.scalars(stmt).all()), total

    # ---- aggregations -------------------------------------------------------------

    def _grouped(self, filters: ExpenseFilters, *group_cols) -> Select:
        return (
            select(
                *group_cols,
                Expense.currency,
                func.sum(Expense.amount_minor).label("total_minor"),
                func.count().label("count"),
                func.min(Expense.amount_minor).label("min_minor"),
                func.max(Expense.amount_minor).label("max_minor"),
            )
            .where(*build_conditions(filters))
            .group_by(*group_cols, Expense.currency)
        )

    def totals_by_currency(self, filters: ExpenseFilters):
        # Only the summary needs the distinct-user count (it is the most expensive aggregate).
        users = func.count(func.distinct(Expense.user_id)).label("users")
        stmt = self._grouped(filters).add_columns(users).order_by(Expense.currency)
        return self.session.execute(stmt).all()

    def totals_by_category(self, filters: ExpenseFilters):
        stmt = self._grouped(filters, Expense.category).order_by(
            Expense.currency, func.sum(Expense.amount_minor).desc()
        )
        return self.session.execute(stmt).all()

    def totals_by_month(self, filters: ExpenseFilters):
        month = func.strftime("%Y-%m", Expense.expense_date).label("month")  # SQLite function
        stmt = self._grouped(filters, month).order_by(month, Expense.currency)
        return self.session.execute(stmt).all()

    def totals_by_category_month(self, filters: ExpenseFilters):
        month = func.strftime("%Y-%m", Expense.expense_date).label("month")
        stmt = self._grouped(filters, Expense.category, month).order_by(
            month, Expense.currency, Expense.category
        )
        return self.session.execute(stmt).all()

    def totals_by_user(self, filters: ExpenseFilters, limit: int | None = None):
        """Spend per user, biggest first within each currency.

        ``limit`` keeps only the top N users *per currency* (a window function ranks users
        inside each currency), so a leaderboard stays small however many users exist.
        """
        grouped = (
            self._grouped(filters, Expense.user_id, User.name)
            .select_from(Expense)
            .join(User, User.id == Expense.user_id)
        )
        if limit is None:
            stmt = grouped.order_by(
                Expense.currency, func.sum(Expense.amount_minor).desc(), Expense.user_id
            )
            return self.session.execute(stmt).all()
        rank = (
            func.row_number()
            .over(partition_by=Expense.currency, order_by=func.sum(Expense.amount_minor).desc())
            .label("rank")
        )
        ranked = grouped.add_columns(rank).subquery()
        stmt = (
            select(ranked)
            .where(ranked.c.rank <= limit)
            .order_by(ranked.c.currency, ranked.c.rank, ranked.c.user_id)
        )
        return self.session.execute(stmt).all()

    def _by_owner_attribute(self, filters: ExpenseFilters, column):
        stmt = (
            self._grouped(filters, column)
            .select_from(Expense)
            .join(User, User.id == Expense.user_id)
            .order_by(Expense.currency, func.sum(Expense.amount_minor).desc())
        )
        return self.session.execute(stmt).all()

    def totals_by_country(self, filters: ExpenseFilters):
        return self._by_owner_attribute(filters, User.country)

    def totals_by_merchant(self, filters: ExpenseFilters):
        stmt = self._grouped(filters, Expense.merchant).order_by(
            Expense.currency, func.sum(Expense.amount_minor).desc(), Expense.merchant
        )
        return self.session.execute(stmt).all()

    def totals_by_payment_method(self, filters: ExpenseFilters):
        stmt = self._grouped(filters, Expense.payment_method).order_by(
            Expense.currency, func.sum(Expense.amount_minor).desc()
        )
        return self.session.execute(stmt).all()

    def active_users_by_month(self, filters: ExpenseFilters):
        """Distinct users with at least one expense per month (a 'monthly active users' proxy)."""
        month = func.strftime("%Y-%m", Expense.expense_date).label("month")
        stmt = (
            select(
                month,
                func.count(func.distinct(Expense.user_id)).label("active_users"),
                func.count().label("expenses"),
            )
            .where(*build_conditions(filters))
            .group_by(month)
            .order_by(month)
        )
        return self.session.execute(stmt).all()

    def totals_by_weekday(self, filters: ExpenseFilters):
        weekday = func.strftime("%w", Expense.expense_date).label("weekday")  # 0 = Sunday
        stmt = self._grouped(filters, weekday).order_by(Expense.currency, weekday)
        return self.session.execute(stmt).all()

    def totals_by_day(self, filters: ExpenseFilters):
        stmt = self._grouped(filters, Expense.expense_date).order_by(
            Expense.expense_date, Expense.currency
        )
        return self.session.execute(stmt).all()

    def category_counts(self, user_id: int | None, q: str | None, sort_key: str, descending: bool):
        count = func.count().label("count")
        stmt = (
            select(Expense.category, count)
            .where(
                Expense.category.is_not(None),
                *build_conditions(ExpenseFilters(user_ids=[user_id] if user_id else None)),
            )
            .group_by(Expense.category)
        )
        if q:
            stmt = stmt.where(Expense.category.ilike(f"%{_like_escape(q)}%", escape="\\"))
        column = count if sort_key == "count" else Expense.category
        stmt = stmt.order_by(column.desc() if descending else column.asc(), Expense.category)
        return self.session.execute(stmt).all()
