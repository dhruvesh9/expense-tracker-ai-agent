"""Database engine and session management.

* Engine  - owns the connection pool; created once per process.
* Session - a short-lived "unit of work": it tracks the objects you load/change
  and sends them to the database in one transaction on ``commit()``.
"""

import logging
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

logger = logging.getLogger(__name__)


def build_engine(database_url: str, echo: bool = False) -> Engine:
    url = make_url(database_url)
    kwargs: dict = {}
    if url.get_backend_name() == "sqlite":
        # FastAPI may use a connection from a different thread than the one that created it.
        kwargs["connect_args"] = {"check_same_thread": False}
        if url.database in (None, "", ":memory:"):
            # An in-memory DB vanishes per connection; StaticPool shares one (used by tests).
            kwargs["poolclass"] = StaticPool
        else:
            Path(url.database).parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(url, echo=echo, **kwargs)

    if url.get_backend_name() == "sqlite":

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_connection, _record) -> None:
            # SQLite does NOT enforce foreign keys unless asked, per connection.
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")  # wait up to 5s on a locked DB
            cursor.close()

    return engine


engine = build_engine(settings.database_url, echo=False)  # SQL logging goes via logging_config
# expire_on_commit=False keeps objects readable after commit (no surprise re-query).
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: give each request its own Session and always close it.

    Services call ``session.commit()`` explicitly when a business operation succeeds.
    If an exception escapes before that, ``close()`` discards the uncommitted
    transaction (an implicit rollback), so half-finished work never reaches the DB.
    """
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
