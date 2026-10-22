from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import PageParam, PageSizeParam, UserFiltersDep, UserServiceDep
from app.api.fields import FieldsParam, build_item, build_page, parse_fields
from app.schemas.common import Page
from app.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

UserSortParam = Annotated[
    str,
    Query(
        pattern=r"^-?(id|name|created_at|updated_at)$",
        description="Field to sort by; prefix with '-' for descending",
    ),
]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, service: UserServiceDep, response: Response):
    """`payload` is validated by Pydantic before this function body runs."""
    user = service.create_user(payload)
    response.headers["Location"] = f"/api/v1/users/{user.id}"
    return user


@router.get("", response_model=Page[UserRead])
def list_users(
    service: UserServiceDep,
    filters: UserFiltersDep,
    sort: UserSortParam = "id",
    page: PageParam = 1,
    page_size: PageSizeParam = 20,
    fields: FieldsParam = None,
):
    """Filter (all combine with AND), sort, paginate; `fields=id,name` trims the response."""
    selected = parse_fields(fields, UserRead)
    users, total = service.list_users(filters, sort, page, page_size)
    return build_page(UserRead, users, total, page, page_size, selected)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, service: UserServiceDep, fields: FieldsParam = None):
    selected = parse_fields(fields, UserRead)
    return build_item(UserRead, service.get_user(user_id), selected)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: int, payload: UserUpdate, service: UserServiceDep):
    return service.update_user(user_id, payload)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, service: UserServiceDep, delete_expenses: bool = False):
    service.delete_user(user_id, delete_expenses)
