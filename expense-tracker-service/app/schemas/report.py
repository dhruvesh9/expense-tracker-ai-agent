from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class CurrencyTotal(BaseModel):
    """Totals are ALWAYS per currency; different currencies are never added together."""

    currency: str
    total: Decimal
    count: int


class CurrencySummary(CurrencyTotal):
    users: int  # distinct users with at least one matching expense
    average: Decimal  # total / count, rounded to 2 decimals (a statistic, not a ledger value)
    minimum: Decimal
    maximum: Decimal


class CategoryTotal(CurrencyTotal):
    category: str | None  # null = expenses without a category


class MonthTotal(CurrencyTotal):
    month: str  # "YYYY-MM"


class CategoryMonthTotal(CategoryTotal):
    month: str  # "YYYY-MM"


class UserTotal(CurrencyTotal):
    user_id: int
    name: str


class CountryTotal(CurrencyTotal):
    country: str | None  # ISO code; null = users without a country


class MerchantTotal(CurrencyTotal):
    merchant: str | None  # null = expenses without a merchant


class PaymentMethodTotal(CurrencyTotal):
    payment_method: str | None


class WeekdayTotal(CurrencyTotal):
    weekday: int  # 0 = Monday ... 6 = Sunday
    name: str  # "Mon" ... "Sun"


class DayTotal(CurrencyTotal):
    day: date


class SummaryReport(BaseModel):
    total_count: int
    by_currency: list[CurrencySummary]


class CategorySummary(BaseModel):
    items: list[CategoryTotal]


class MonthlySummary(BaseModel):
    items: list[MonthTotal]


class CategoryMonthlySummary(BaseModel):
    items: list[CategoryMonthTotal]


class UserSummary(BaseModel):
    items: list[UserTotal]


class CountrySummary(BaseModel):
    items: list[CountryTotal]


class MerchantSummary(BaseModel):
    items: list[MerchantTotal]


class PaymentMethodSummary(BaseModel):
    items: list[PaymentMethodTotal]


class SignupMonth(BaseModel):
    month: str  # "YYYY-MM"
    new_users: int
    total_users: int  # cumulative, including everyone who signed up before the first month listed


class UserGrowth(BaseModel):
    items: list[SignupMonth]


class ActiveMonth(BaseModel):
    month: str
    active_users: int  # distinct users with at least one expense that month
    expenses: int


class ActiveUsers(BaseModel):
    items: list[ActiveMonth]


class BudgetStatus(BaseModel):
    user_id: int
    name: str
    currency: str
    budget: Decimal
    spent: Decimal
    remaining: Decimal  # negative when over budget
    percent_used: float
    status: str  # "ok" (< 80%), "near" (80-100%), "over" (> 100%)


class BudgetCounts(BaseModel):
    total: int  # users with a budget (matching the user filters)
    ok: int
    near: int
    over: int


class BudgetReport(BaseModel):
    month: str
    counts: BudgetCounts
    items: list[BudgetStatus]  # worst first, at most `limit`


class WeekdaySummary(BaseModel):
    items: list[WeekdayTotal]


class DailySummary(BaseModel):
    items: list[DayTotal]


class CategoryInfo(BaseModel):
    category: str
    count: int
