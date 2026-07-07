"""Domain exceptions and structured error handling."""

from typing import Any


class AppError(Exception):
    """Base application error with structured error code and detail."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(message)


class NotFoundError(AppError):
    """Resource not found."""

    def __init__(self, resource: str, resource_id: str | None = None) -> None:
        msg = f"{resource} not found"
        super().__init__(
            code="not_found",
            message=msg,
            status_code=404,
            detail={"resource": resource, "id": resource_id},
        )


class ValidationError(AppError):
    """Input validation failed."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(
            code="validation_error",
            message=message,
            status_code=422,
            detail={"field": field} if field else {},
        )


class PermissionDeniedError(AppError):
    """User lacks permission for this action."""

    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(
            code="permission_denied",
            message=message,
            status_code=403,
        )


class RateLimitError(AppError):
    """Rate limit exceeded."""

    def __init__(self) -> None:
        super().__init__(
            code="rate_limit_exceeded",
            message="Too many requests. Please try again later.",
            status_code=429,
        )


class ExternalServiceError(AppError):
    """External service (OpenAI, Qdrant) failed."""

    def __init__(self, service: str, message: str = "Service unavailable") -> None:
        super().__init__(
            code="external_service_error",
            message=message,
            status_code=502,
            detail={"service": service},
        )
