from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Standard envelope for every list endpoint. ``Generic[T]`` lets one class
    describe ``Page[UserRead]``, ``Page[ExpenseRead]``, ..."""

    items: list[T]
    total: int = Field(description="Total matching rows across all pages")
    page: int
    page_size: int
    pages: int = Field(description="Total number of pages")


class ErrorBody(BaseModel):
    code: str
    message: str
    details: object | None = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


def make_page(items: list, total: int, page: int, page_size: int) -> dict:
    pages = (total + page_size - 1) // page_size  # ceiling division
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}
