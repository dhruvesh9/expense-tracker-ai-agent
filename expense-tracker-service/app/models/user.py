from decimal import Decimal

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.money import from_minor_units


class User(TimestampMixin, Base):
    """An end user of the expense tracker. Deliberately minimal personal data."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(2))  # ISO 3166-1 alpha-2, upper-case
    city: Mapped[str | None] = mapped_column(String(80))  # helps tell people apart, e.g. "Pune"
    # The currency this person mostly spends in; budgets are expressed in it.
    default_currency: Mapped[str] = mapped_column(String(3), default="INR", server_default="INR")
    # Optional monthly spending target in minor units (same convention as expenses.amount_minor).
    monthly_budget_minor: Mapped[int | None] = mapped_column(BigInteger)

    @property
    def monthly_budget(self) -> Decimal | None:
        """Decimal view of ``monthly_budget_minor``; this is what the API schema reads."""
        if self.monthly_budget_minor is None:
            return None
        return from_minor_units(self.monthly_budget_minor)
