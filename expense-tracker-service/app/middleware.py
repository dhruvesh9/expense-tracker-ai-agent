"""Request-tracing middleware: assigns a request ID and logs start/finish."""

import logging
import time
import uuid

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.config import settings
from app.logging_config import request_id_var

logger = logging.getLogger("app.request")

# Tiny in-process cache for report GETs: dashboards ask for the same aggregates over millions of
# rows again and again. Entries live `report_cache_seconds`; ANY write (POST/PATCH/DELETE under
# /api/) clears everything, so users never see stale numbers after changing data.
_report_cache: dict[str, tuple[float, int, bytes, str]] = {}


async def request_context_middleware(request: Request, call_next):
    """Runs around every request. ``call_next`` runs the rest of the app.

    Also the last line of defence: unexpected exceptions are logged with a stack
    trace and converted to a generic 500 (internals are never leaked to clients).
    """
    # Honour an ID sent by the caller (lets the agent correlate its own logs).
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    token = request_id_var.set(request_id)
    start = time.perf_counter()
    # Static console files are noisy (dozens of requests per page load): log them at DEBUG.
    is_static = request.url.path.startswith("/console")
    quiet_level = logging.DEBUG if is_static else logging.INFO
    logger.log(quiet_level, "request_started method=%s path=%s", request.method, request.url.path)

    path = request.url.path
    cache_key = None
    if settings.report_cache_seconds > 0:
        if request.method != "GET" and path.startswith("/api/"):
            _report_cache.clear()
        elif request.method == "GET" and path.startswith("/api/v1/reports"):
            cache_key = f"{path}?{request.url.query}"
            hit = _report_cache.get(cache_key)
            if hit and time.monotonic() - hit[0] < settings.report_cache_seconds:
                logger.debug("report_cache_hit path=%s", path)
                cached = Response(content=hit[2], status_code=hit[1], media_type=hit[3])
                cached.headers["X-Cache"] = "HIT"
                cached.headers["X-Request-ID"] = request_id
                request_id_var.reset(token)
                return cached

    try:
        response = await call_next(request)
        if cache_key and response.status_code == 200:
            body = b"".join([chunk async for chunk in response.body_iterator])
            _report_cache[cache_key] = (
                time.monotonic(),
                200,
                body,
                response.media_type or "application/json",
            )
            response = Response(content=body, status_code=200, media_type=response.media_type)
    except Exception:
        logger.exception("unhandled_exception")
        response = JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Internal server error",
                    "details": None,
                    "request_id": request_id,
                }
            },
        )

    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    if is_static:
        response.headers["Cache-Control"] = "no-cache"  # always revalidate (ETag) while developing
    level = logging.WARNING if response.status_code >= 400 else quiet_level
    logger.log(
        level,
        "request_completed status=%s duration_ms=%.1f",
        response.status_code,
        duration_ms,
    )
    request_id_var.reset(token)
    return response
