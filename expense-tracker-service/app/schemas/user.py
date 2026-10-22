from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Country = Annotated[str, Field(pattern=r"^[A-Za-z]{2}$", examples=["IN"])]
Currency = Annotated[str, Field(pattern=r"^[A-Za-z]{3}$", examples=["INR"])]
Budget = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2, examples=["50000.00"])]


def _clean_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("name must not be blank")
    return value


class UserFields(BaseModel):
    """Cleaning rules shared by create and update."""

    @field_validator("name", check_fields=False)
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        return None if value is None else _clean_name(value)

    @field_validator("city", check_fields=False)
    @classmethod
    def _city(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None

    @field_validator("country", "default_currency", check_fields=False)
    @classmethod
    def _upper(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class UserCreate(UserFields):
    name: str = Field(min_length=1, max_length=100, examples=["Asha"])
    country: Country | None = None
    city: str | None = Field(default=None, max_length=80, examples=["Pune"])
    default_currency: Currency = "INR"
    monthly_budget: Budget | None = Field(
        default=None, description="Optional monthly spending target in default_currency"
    )


class UserUpdate(UserFields):
    """PATCH body: send only what changes. country / monthly_budget may be null to clear."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    country: Country | None = None
    city: str | None = Field(default=None, max_length=80)
    default_currency: Currency | None = None
    monthly_budget: Budget | None = None

    @model_validator(mode="after")
    def _required_fields_cannot_be_null(self) -> "UserUpdate":
        for field in ("name", "default_currency"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class UserRead(BaseModel):
    # from_attributes lets Pydantic read values from an ORM object (user.name)
    # instead of requiring a dict.
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    country: str | None
    city: str | None
    default_currency: str
    monthly_budget: Decimal | None  # read from the ORM property User.monthly_budget
    created_at: datetime
    updated_at: datetime
