"""Logging setup with request-ID tracing.

Problem: many requests run concurrently and their log lines interleave. Solution:
store the current request's ID in a ``ContextVar`` (a variable whose value is
separate for each async task / request) and a logging Filter copies it onto every
log record, so *any* module's log line automatically carries ``request_id=...``.
"""

import logging
from contextvars import ContextVar

from app.config import settings

# "-" is shown for log lines produced outside a request (e.g. at startup).
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True  # True = keep the record


def configure_logging() -> None:
    """Install one console handler on the root logger. Safe to call repeatedly."""
    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-5s request_id=%(request_id)s %(name)s | %(message)s"
        )
    )

    root = logging.getLogger()
    root.handlers = [handler]  # replace, so repeated calls don't duplicate lines
    root.setLevel(settings.log_level)

    # Our middleware logs each request, so silence uvicorn's duplicate access log.
    logging.getLogger("uvicorn.access").disabled = True
    # SQL statements are logged by SQLAlchemy only when SQL_ECHO=true.
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.sql_echo else logging.WARNING
    )
