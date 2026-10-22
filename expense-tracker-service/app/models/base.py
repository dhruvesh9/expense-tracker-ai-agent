"""Shared base class and column types for ORM models.

ORM models describe *database tables*. They are different from the Pydantic
schemas in ``app/schemas`` which describe *API payloads*. Keeping them separate
means you can change the table layout without breaking the API (and vice versa).
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """Store timezone-aware datetimes in SQLite (which has no timezone support).

    On the way in we convert to UTC; on the way out we re-attach the UTC tzinfo.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return value.astimezone(UTC).replace(tzinfo=None) if value is not None else None

    def process_result_value(self, value, dialect):
        return value.replace(tzinfo=UTC) if value is not None else None


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """Adds created_at / updated_at to any model that inherits it.

    ``onupdate`` makes SQLAlchemy refresh updated_at whenever the row is UPDATEd.
    """

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
