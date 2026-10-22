from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, Integer, String, false
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.money import from_minor_units


class Expense(TimestampMixin, Base):
    """One spending record.

    Two different times are stored on purpose:
      * ``expense_date``  - when the money was actually spent (chosen by the user)
      * ``created_at``/``updated_at`` - when this *record* was inserted/modified
    """

    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="ck_expenses_amount_positive"),
        CheckConstraint(
            "payment_method IN ('cash', 'credit_card', 'debit_card', 'bank_transfer', "
            "'digital_wallet', 'other')",
            name="ck_expenses_payment_method",
        ),
        # Indexes speed up the most common filters/sorts.
        Index("ix_expenses_user_date", "user_id", "expense_date"),
        Index("ix_expenses_category", "category"),
        Index("ix_expenses_date", "expense_date"),
        # Covering indexes for the reports: each holds every column its report reads, so the
        # database answers from the index alone and never touches the (huge) table.
        Index("ix_expenses_report_core", "currency", "expense_date", "amount_minor", "user_id"),
        Index(
            "ix_expenses_report_category", "currency", "expense_date", "category", "amount_minor"
        ),
        Index(
            "ix_expenses_report_merchant",
            "currency",
            "expense_date",
            "merchant",
            "payment_method",
            "amount_minor",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # RESTRICT: the database itself refuses to delete a user who still has expenses.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    amount_minor: Mapped[int] = mapped_column(Integer)  # 25050 == 250.50
    currency: Mapped[str] = mapped_column(String(3), default="INR")  # ISO-4217 style, upper-case
    description: Mapped[str | None] = mapped_column(String(500))
    category: Mapped[str | None] = mapped_column(String(50))  # normalised to lower-case
    expense_date: Mapped[date] = mapped_column(Date)
    merchant: Mapped[str | None] = mapped_column(String(100))  # where the money went
    payment_method: Mapped[str | None] = mapped_column(String(20))  # see the CHECK above
    # Subscriptions, rent, bills: fixed costs that repeat, as opposed to one-off spending.
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    @property
    def amount(self) -> Decimal:
        """Decimal view of ``amount_minor``; this is what the API schema reads."""
        return from_minor_units(self.amount_minor)
