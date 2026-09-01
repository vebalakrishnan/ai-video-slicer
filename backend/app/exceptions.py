"""Custom application exceptions.

Raised anywhere in routers/services and translated into a uniform JSON
error body by the global exception handler registered in app/main.py:
    {"error": exc.code, "message": exc.message}
"""


class AppException(Exception):
    """Base application exception. All custom errors should subclass this."""

    def __init__(self, message: str, code: str, status_code: int = 500) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppException):
    """Raised when a requested resource does not exist. Maps to HTTP 404."""

    def __init__(self, resource: str) -> None:
        super().__init__(f"{resource} not found", "NOT_FOUND", 404)


class ConflictError(AppException):
    """Raised when a request conflicts with existing state. Maps to HTTP 409."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "CONFLICT", 409)


class ValidationError(AppException):
    """Raised when request input fails validation. Maps to HTTP 400."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "VALIDATION_ERROR", 400)


class UnauthorizedError(AppException):
    """Raised when authentication/authorization fails. Maps to HTTP 401."""

    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message, "UNAUTHORIZED", 401)
