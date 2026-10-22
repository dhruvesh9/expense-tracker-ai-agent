"""Application exceptions and the JSON error format.

Business code raises these exceptions; the handlers registered in ``main.py``
turn them into a consistent response:

    {"error": {"code": "...", "message": "...", "details": ..., "request_id": "..."}}
"""


class AppError(Exception):
    """Base class: carries an HTTP status and a machine-readable code."""

    status_code = 400
    code = "app_error"

    def __init__(self, message: str, details: object | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    """The request is valid but clashes with current state (e.g. user still has expenses)."""

    status_code = 409
    code = "conflict"


class InvalidReferenceError(AppError):
    """A field in the body points at something that doesn't exist (e.g. unknown user_id)."""

    status_code = 422
    code = "invalid_reference"
