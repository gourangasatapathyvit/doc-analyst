"""Correlation ID middleware — assigns request_id + session_id to structlog context."""

from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:8])
        session_id = request.headers.get("X-Session-ID", "")

        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            session_id=session_id,
        )

        start = time.perf_counter()
        logger.info("request_started", method=request.method, path=str(request.url.path))

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.info(
            "request_completed",
            status=response.status_code,
            duration_ms=duration_ms,
        )

        structlog.contextvars.unbind_contextvars("request_id", "session_id")
        response.headers["X-Request-ID"] = request_id
        return response
