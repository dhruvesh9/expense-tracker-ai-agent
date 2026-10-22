"""Application entry point: ``uvicorn app.main:app``."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import health
from app.api.v1.router import api_router
from app.config import settings
from app.errors import AppError
from app.logging_config import configure_logging, request_id_var
from app.middleware import request_context_middleware
from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)

CONSOLE_DIR = Path(__file__).parent / "console"  # static admin console (HTML/CSS/JS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Code before ``yield`` runs at startup, code after it at shutdown."""
    configure_logging()
    logger.info("service_starting env=%s log_level=%s", settings.app_env, settings.log_level)
    yield
    logger.info("service_stopped")


def _error(status_code: int, code: str, message: str, details=None) -> JSONResponse:
    body = {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id_var.get(),
        }
    }
    return JSONResponse(status_code=status_code, content=body)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Expense Tracker Service",
        version="1.0.0",
        description="REST backend owning users and expenses. Local use only: no authentication.",
        lifespan=lifespan,
        debug=False,
    )
    app.middleware("http")(request_context_middleware)

    # Every error response uses the same JSON shape (documented as ErrorResponse).
    error_docs = {404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}}

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError):
        logger.info("business_error code=%s message=%s", exc.code, exc.message)
        return _error(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError):
        # Log only where/why it failed, never the submitted values (could be sensitive).
        errors = [
            {"location": ".".join(str(p) for p in e["loc"]), "message": e["msg"], "type": e["type"]}
            for e in exc.errors()
        ]
        logger.warning("validation_failed fields=%s", [e["location"] for e in errors])
        return _error(422, "validation_error", "Request validation failed", errors)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, exc: StarletteHTTPException):
        return _error(exc.status_code, "http_error", str(exc.detail))

    app.include_router(health.router)
    app.include_router(api_router, prefix="/api/v1", responses=error_docs)

    # The admin console is plain static files served from the same process, so it can
    # call the API on the same origin (no CORS setup needed).
    app.mount("/console", StaticFiles(directory=CONSOLE_DIR, html=True), name="console")

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse("/console/")

    return app


app = create_app()
