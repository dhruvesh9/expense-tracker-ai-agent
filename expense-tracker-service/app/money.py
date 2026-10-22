"""Exact money handling.

Floats cannot represent 0.1 exactly, so we never use them for money. Amounts are
``Decimal`` in Python and stored in SQLite as an INTEGER count of *minor units*
(paise/cents): 250.50 -> 25050. Integers are exact, sortable and SUM()-able in SQL.

Limitation (documented in docs/database.md): every currency is assumed to have 2
decimal places, so JPY-style 0-decimal and KWD-style 3-decimal currencies are not modelled.
"""

from decimal import Decimal

MINOR_UNITS_PER_MAJOR = 100


def to_minor_units(amount: Decimal) -> int:
    """250.50 -> 25050. Raises ValueError if ``amount`` has more than 2 decimals."""
    scaled = amount * MINOR_UNITS_PER_MAJOR
    if scaled != scaled.to_integral_value():
        raise ValueError("amount has more than 2 decimal places")
    return int(scaled)


def from_minor_units(minor: int) -> Decimal:
    """25050 -> Decimal('250.50') (always exactly 2 decimal places)."""
    return Decimal(minor).scaleb(-2)
