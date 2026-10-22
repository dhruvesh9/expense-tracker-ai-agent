"""Sparse field selection: ``?fields=id,name`` returns only those fields.

Smaller responses are cheaper for a caller (especially an LLM agent paying per token).
Note this trims the *response payload*; the database row is still loaded in full,
which is cheap for these tiny tables.
"""

from typing import Annotated

from fastapi import HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.schemas.common import make_page

FieldsParam = Annotated[
    str | None,
    Query(description="Comma-separated fields to return, e.g. fields=id,name (default: all)"),
]


def parse_fields(fields: str | None, schema: type[BaseModel]) -> set[str] | None:
    """Validate the ``fields`` query value against the response schema's field names."""
    if fields is None or not fields.strip():
        return None
    requested = {name.strip() for name in fields.split(",") if name.strip()}
    allowed = set(schema.model_fields)
    unknown = requested - allowed
    if unknown:
        raise HTTPException(
            422,
            f"Unknown field(s): {sorted(unknown)}. Allowed: {sorted(allowed)}",
        )
    return requested


def build_item(schema: type[BaseModel], obj, fields: set[str] | None):
    """One resource. Without ``fields`` return the ORM object so FastAPI's normal
    response_model validation applies; with ``fields`` return the trimmed JSON directly
    (response_model would reject a partial object because it requires every field)."""
    if fields is None:
        return obj
    return JSONResponse(schema.model_validate(obj).model_dump(mode="json", include=fields))


def build_page(schema: type[BaseModel], rows: list, total: int, page: int, page_size: int, fields):
    """A paginated list envelope, trimmed to ``fields`` when given."""
    if fields is None:
        return make_page(rows, total, page, page_size)
    items = [schema.model_validate(r).model_dump(mode="json", include=fields) for r in rows]
    return JSONResponse(make_page(items, total, page, page_size))
