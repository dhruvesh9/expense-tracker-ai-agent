from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.api.deps import ExpenseServiceDep
from app.api.fields import FieldsParam, parse_fields
from app.schemas.report import CategoryInfo

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryInfo])
def list_categories(
    service: ExpenseServiceDep,
    user_id: Annotated[int | None, Query(gt=0)] = None,
    q: Annotated[str | None, Query(description="Category name contains")] = None,
    sort: Annotated[
        str, Query(pattern=r"^-?(category|count)$", description="'-' prefix = descending")
    ] = "category",
    fields: FieldsParam = None,
):
    """Categories are free-form labels on expenses; this lists the ones in use
    (handy for an agent to reuse existing names instead of inventing duplicates)."""
    selected = parse_fields(fields, CategoryInfo)
    rows = service.list_categories(user_id, q.strip().lower() if q else None, sort)
    items = [CategoryInfo(category=c, count=n) for c, n in rows]
    if selected is None:
        return items
    return JSONResponse([i.model_dump(mode="json", include=selected) for i in items])
