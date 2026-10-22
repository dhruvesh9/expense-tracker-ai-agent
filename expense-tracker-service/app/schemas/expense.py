from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Reusable annotated types. Pydantic rejects (never rounds) amounts with more than
# 2 decimals, and Decimal values are serialised to JSON as exact strings ("250.50").
Amount = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2, examples=["250.00"])]
Currency = Annotated[str, Field(pattern=r"^[A-Za-z]{3}$", examples=["INR"])]
# The allowed payment methods are also enforced by a CHECK constraint in the database.
PaymentMethod = Literal[
    "cash", "credit_card", "debit_card", "bank_transfer", "digital_wallet", "other"
]


def _normalise_category(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip().lower()
    return value or None


def _normalise_description(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


class ExpenseBase(BaseModel):
    @field_validator("currency", check_fields=False)
    @classmethod
    def _upper_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value

    @field_validator("category", check_fields=False)
    @classmethod
    def _category(cls, value: str | None) -> str | None:
        return _normalise_category(value)

    @field_validator("merchant", check_fields=False)
    @classmethod
    def _merchant(cls, value: str | None) -> str | None:
        return _normalise_description(value)

    @field_validator("description", check_fields=False)
    @classmethod
    def _description(cls, value: str | None) -> str | None:
        return _normalise_description(value)


class ExpenseCreate(ExpenseBase):
    user_id: int = Field(gt=0)
    amount: Amount
    currency: Currency = "INR"
    description: str | None = Field(default=None, max_length=500, examples=["Lunch"])
    category: str | None = Field(default=None, max_length=50, examples=["food"])
    expense_date: date = Field(description="Day the money was spent (YYYY-MM-DD)")
    merchant: str | None = Field(default=None, max_length=100, examples=["Starbucks"])
    payment_method: PaymentMethod | None = None
    is_recurring: bool = Field(default=False, description="Subscription, rent, bill ...")


class ExpenseUpdate(ExpenseBase):
    """PATCH body: every field optional. We distinguish "not sent" from "sent as null"
    using ``model_fields_set`` (the set of fields the client actually provided)."""

    amount: Amount | None = None
    currency: Currency | None = None
    description: str | None = Field(default=None, max_length=500)
    category: str | None = Field(default=None, max_length=50)
    expense_date: date | None = None
    merchant: str | None = Field(default=None, max_length=100)
    payment_method: PaymentMethod | None = None
    is_recurring: bool | None = None

    @model_validator(mode="after")
    def _no_null_for_required_fields(self) -> "ExpenseUpdate":
        for name in ("amount", "currency", "expense_date", "is_recurring"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class ExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    amount: Decimal  # read from the ORM property Expense.amount
    currency: str
    description: str | None
    category: str | None
    expense_date: date
    merchant: str | None
    payment_method: str | None
    is_recurring: bool
    created_at: datetime
    updated_at: datetime


ExpenseSortField = Literal["expense_date", "amount", "created_at", "id"]
