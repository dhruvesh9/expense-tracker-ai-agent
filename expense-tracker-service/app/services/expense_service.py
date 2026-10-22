import logging

from sqlalchemy.orm import Session

from app.errors import InvalidReferenceError, NotFoundError
from app.models import Expense
from app.money import to_minor_units
from app.repositories.expense_repository import ExpenseFilters, ExpenseRepository
from app.repositories.user_repository import UserRepository
from app.schemas.expense import ExpenseCreate, ExpenseUpdate

logger = logging.getLogger(__name__)


class ExpenseService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.expenses = ExpenseRepository(session)
        self.users = UserRepository(session)

    def create_expense(self, data: ExpenseCreate) -> Expense:
        logger.debug("component=expense_service action=create_expense")
        if self.users.get(data.user_id) is None:
            raise InvalidReferenceError(f"User {data.user_id} does not exist")
        expense = Expense(
            user_id=data.user_id,
            amount_minor=to_minor_units(data.amount),
            currency=data.currency,
            description=data.description,
            category=data.category,
            expense_date=data.expense_date,
            merchant=data.merchant,
            payment_method=data.payment_method,
            is_recurring=data.is_recurring,
        )
        self.expenses.add(expense)
        self.session.commit()  # the whole operation succeeds or fails as one unit
        logger.info("expense_created expense_id=%s user_id=%s", expense.id, expense.user_id)
        return expense

    def get_expense(self, expense_id: int) -> Expense:
        expense = self.expenses.get(expense_id)
        if expense is None:
            raise NotFoundError(f"Expense {expense_id} not found")
        return expense

    def list_expenses(
        self, filters: ExpenseFilters, sort: str, page: int, page_size: int
    ) -> tuple[list[Expense], int]:
        descending = sort.startswith("-")
        return self.expenses.search(filters, sort.lstrip("-"), descending, page, page_size)

    def update_expense(self, expense_id: int, data: ExpenseUpdate) -> Expense:
        expense = self.get_expense(expense_id)
        # exclude_unset=True => only fields the client really sent; others stay untouched.
        changes = data.model_dump(exclude_unset=True)
        if "amount" in changes:
            expense.amount_minor = to_minor_units(changes.pop("amount"))
        for field, value in changes.items():
            setattr(expense, field, value)
        self.session.commit()
        logger.info(
            "expense_updated expense_id=%s fields=%s", expense_id, sorted(data.model_fields_set)
        )
        return expense

    def delete_expense(self, expense_id: int) -> None:
        expense = self.get_expense(expense_id)
        self.expenses.delete(expense)
        self.session.commit()
        logger.info("expense_deleted expense_id=%s", expense_id)

    def list_categories(self, user_id: int | None, q: str | None, sort: str):
        return self.expenses.category_counts(user_id, q, sort.lstrip("-"), sort.startswith("-"))
