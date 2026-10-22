import logging

from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError
from app.models import User
from app.money import to_minor_units
from app.repositories.user_repository import UserFilters, UserRepository
from app.schemas.user import UserCreate, UserUpdate

logger = logging.getLogger(__name__)


def _budget_minor(budget):
    """Decimal budget (or None = no budget) -> integer minor units for the database."""
    return None if budget is None else to_minor_units(budget)


class UserService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)

    def create_user(self, data: UserCreate) -> User:
        logger.debug("component=user_service action=create_user")
        user = self.users.add(
            name=data.name,
            country=data.country,
            city=data.city,
            default_currency=data.default_currency,
            monthly_budget_minor=_budget_minor(data.monthly_budget),
        )
        self.session.commit()
        logger.info("user_created user_id=%s", user.id)
        return user

    def get_user(self, user_id: int) -> User:
        user = self.users.get(user_id)
        if user is None:
            raise NotFoundError(f"User {user_id} not found")
        return user

    def list_users(self, filters: UserFilters, sort: str, page: int, page_size: int):
        return self.users.list(filters, sort.lstrip("-"), sort.startswith("-"), page, page_size)

    def update_user(self, user_id: int, data: UserUpdate) -> User:
        user = self.get_user(user_id)
        # exclude_unset=True: only the fields the client actually sent are changed.
        changes = data.model_dump(exclude_unset=True)
        if "monthly_budget" in changes:
            changes["monthly_budget_minor"] = _budget_minor(changes.pop("monthly_budget"))
        for field, value in changes.items():
            setattr(user, field, value)
        self.session.commit()
        logger.info("user_updated user_id=%s", user_id)
        return user

    def delete_user(self, user_id: int, delete_expenses: bool) -> None:
        user = self.get_user(user_id)
        expense_count = self.users.count_expenses(user_id)
        if expense_count and not delete_expenses:
            # 409 Conflict: tell the caller how to proceed rather than silently destroying data.
            raise ConflictError(
                f"User {user_id} still has {expense_count} expense(s). "
                "Delete them first or pass delete_expenses=true.",
                details={"expense_count": expense_count},
            )
        if expense_count:
            self.users.delete_expenses(user_id)
        self.users.delete(user)
        self.session.commit()  # expenses + user are removed atomically
        logger.info("user_deleted user_id=%s expenses_deleted=%s", user_id, expense_count)
