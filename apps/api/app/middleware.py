from __future__ import annotations

import json
import logging
import time
from collections import defaultdict, deque
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import get_settings

logger = logging.getLogger("mireye.api")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid4()))
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "latency_ms": round((time.perf_counter() - started) * 1000),
                }
            )
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int = 120, window_seconds: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window_seconds
        self.requests: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        # Browser CORS negotiation is infrastructure traffic, not an API call.
        # Counting it makes a polling UI consume the allowance twice as fast.
        if request.method == "OPTIONS" or request.url.path == "/health":
            return await call_next(request)
        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        bucket = self.requests[key]
        while bucket and bucket[0] < now - self.window:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
        bucket.append(now)
        return await call_next(request)


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        expected = get_settings().app_api_key
        if expected and request.url.path.startswith("/api/"):
            supplied = request.headers.get("authorization", "").removeprefix("Bearer ")
            if supplied != expected:
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)
