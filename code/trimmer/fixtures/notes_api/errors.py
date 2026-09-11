"""Error types and the shape of an error response."""


class AppError(Exception):
    """Base class for every error the application raises deliberately."""

    status = 500

    def __init__(self, message, field=None):
        self.message = message
        self.field = field
        super().__init__(message)


class NotFound(AppError):
    """The requested resource does not exist."""

    status = 404


class ValidationError(AppError):
    """The request body failed validation."""

    status = 422


class Unauthorized(AppError):
    """The caller is not allowed to perform this action."""

    status = 401


def error_response(exc):
    """Turn an AppError into a JSON-serialisable response body."""
    body = {"error": exc.message, "status": exc.status}
    if exc.field:
        body["field"] = exc.field
    return body
