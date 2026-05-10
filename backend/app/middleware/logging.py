import time
import json
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.logger import get_logger

logger = get_logger("http")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Log request
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        response = await call_next(request)

        # Calculate duration
        duration_ms = round((time.time() - start_time) * 1000)

        # Log response
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        return response
