"""Middlewares: request id + log de acesso, headers de segurança e limite de tamanho do corpo."""
import json
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings

access_log = logging.getLogger("app.access")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        response.headers["X-Request-ID"] = request_id
        access_log.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "ms": elapsed_ms,
                    "user_id": getattr(request.state, "user_id", None),
                    "dev_auth": not settings.auth_enabled,
                }
            )
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        h = response.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        h.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
        if not request.url.path.startswith(("/docs", "/redoc", "/openapi.json", "/media")):
            h.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        if settings.is_production:
            h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > settings.max_body_bytes:
            return JSONResponse(
                status_code=413, content={"error": {"code": "payload_too_large", "message": "Corpo muito grande"}}
            )
        return await call_next(request)
