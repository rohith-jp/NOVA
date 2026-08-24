"""Middleware: request logging + in-memory rate limiting.

Rate limiter is intentionally simple (in-memory per-IP sliding window).
It acts as the structural foundation; a Redis-backed limiter will replace
it once Celery / Redis integration is added.
"""

import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


# ---------------------------------------------------------------------------
# Request Logging Middleware
# ---------------------------------------------------------------------------


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs method, path, status code, and wall-clock latency for every request."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        print(
            f"[NOVA] {request.method} {request.url.path} "
            f"-> {response.status_code} ({elapsed_ms:.1f}ms) "
            f"| client={request.client.host if request.client else 'unknown'}"
        )
        return response


# ---------------------------------------------------------------------------
# In-Memory Rate Limiting Middleware
# ---------------------------------------------------------------------------

RATE_LIMIT_WINDOW_SEC = 60
RATE_LIMIT_MAX_CALLS = 120  # requests per minute per IP

_rate_limit_store: dict[str, deque] = defaultdict(deque)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter (in-memory).

    Returns 429 when a client IP exceeds RATE_LIMIT_MAX_CALLS within
    RATE_LIMIT_WINDOW_SEC seconds. WebSocket upgrade paths are skipped.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip for WebSocket upgrades.
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = _rate_limit_store[ip]

        # Evict timestamps outside the sliding window.
        while window and window[0] < now - RATE_LIMIT_WINDOW_SEC:
            window.popleft()

        if len(window) >= RATE_LIMIT_MAX_CALLS:
            return Response(
                content='{"detail":"Too many requests. Please slow down."}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(RATE_LIMIT_WINDOW_SEC)},
            )

        window.append(now)
        return await call_next(request)
