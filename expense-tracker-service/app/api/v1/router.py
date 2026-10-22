from fastapi import APIRouter

from app.api.v1 import categories, expenses, reports, users

api_router = APIRouter()
for module in (users, expenses, categories, reports):
    api_router.include_router(module.router)
