"""ORM models. Importing them here registers every table on ``Base.metadata``
(Alembic and the tests rely on that)."""

from app.models.base import Base
from app.models.expense import Expense
from app.models.user import User

__all__ = ["Base", "Expense", "User"]
