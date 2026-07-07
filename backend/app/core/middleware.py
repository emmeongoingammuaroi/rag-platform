"""Custom middleware — request correlation ID and metrics tracking."""

import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.utils.metrics import metrics


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assigns a unique X-Request-ID to every request/response cycle.

    If the client sends an X-Request-ID header, it is preserved.
    Otherwise a new UUID is generated. The ID is attached to
    ``request.state.request_id`` and returned in the response headers.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process the request, injecting the correlation ID."""
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Records per-request latency and status code for the metrics summary."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = (time.perf_counter() - start) * 1000
        metrics.record_request(response.status_code, latency_ms)
        return response
