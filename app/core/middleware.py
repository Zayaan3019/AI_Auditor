from __future__ import annotations

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from loguru import logger
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.core.config import settings


# Metrics
REQUEST_COUNT = Counter(
    "ai_auditor_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "ai_auditor_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)
ERROR_COUNT = Counter(
    "ai_auditor_http_errors_total",
    "Total HTTP errors",
    ["method", "endpoint", "status"],
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all HTTP requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Log request
        logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client": request.client.host if request.client else None,
            },
        )

        start_time = time.time()

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Record metrics
            endpoint = request.url.path
            REQUEST_COUNT.labels(
                method=request.method, endpoint=endpoint, status=response.status_code
            ).inc()
            REQUEST_LATENCY.labels(method=request.method, endpoint=endpoint).observe(
                duration
            )

            # Log response
            logger.info(
                f"Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": response.status_code,
                    "duration": f"{duration:.3f}s",
                },
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as exc:
            duration = time.time() - start_time

            # Record error metrics
            endpoint = request.url.path
            ERROR_COUNT.labels(
                method=request.method, endpoint=endpoint, status=500
            ).inc()

            logger.error(
                f"Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "duration": f"{duration:.3f}s",
                    "error": str(exc),
                },
            )
            raise


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add unique request ID to all requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not hasattr(request.state, "request_id"):
            request.state.request_id = str(uuid.uuid4())

        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response


def setup_cors(app) -> None:
    """Configure CORS middleware.

    Args:
        app: FastAPI application instance.
    """
    origins = settings.allowed_origins.split(",") if settings.allowed_origins else ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for consistent error handling and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = getattr(request.state, "request_id", "unknown")

            logger.exception(
                f"Unhandled exception in request {request_id}",
                extra={"request_id": request_id, "url": str(request.url)},
            )

            # Return a generic error response
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "request_id": request_id,
                    "message": "An unexpected error occurred. Please try again later.",
                },
                headers={"X-Request-ID": request_id},
            )
