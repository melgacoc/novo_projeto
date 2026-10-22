"""Rate limit em janela fixa, guardado no Redis (vale para várias instâncias da API).

Uso:
- global, por IP, no middleware (`RateLimitMiddleware`);
- por grupo de rota, como dependência: `Depends(rate_limit("login", 5, 60))`.
Se o Redis cair, a requisição passa (fail-open) e o erro vai para o log.
"""
import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.errors import AppError
from app.core.redis import redis_client

log = logging.getLogger("app.ratelimit")


def client_ip(request: Request) -> str:
    # atrás de proxy confiável, o primeiro IP do X-Forwarded-For é o do cliente
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def hit(key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    """Conta uma requisição. Retorna (permitido, segundos até liberar)."""
    if settings.app_env == "test":
        return True, 0
    bucket = int(time.time() // window_seconds)
    redis_key = f"rl:{key}:{bucket}"
    try:
        pipe = redis_client.pipeline()
        pipe.incr(redis_key)
        pipe.expire(redis_key, window_seconds)
        count, _ = pipe.execute()
    except Exception:  # noqa: BLE001
        log.warning("rate limit indisponível (redis)", exc_info=True)
        return True, 0
    if count > limit:
        retry = window_seconds - int(time.time() % window_seconds)
        return False, retry
    return True, 0


def rate_limit(group: str, limit: int, window_seconds: int, per: str = "ip"):
    """Dependência FastAPI. `per` = "ip" ou "user" (usa o id do usuário quando houver)."""

    def _dep(request: Request) -> None:
        ident = client_ip(request)
        if per == "user":
            user_id = getattr(request.state, "user_id", None)
            if user_id:
                ident = f"u{user_id}"
        ok, retry = hit(f"{group}:{ident}", limit, window_seconds)
        if not ok:
            raise AppError(
                429, "rate_limited", "Muitas requisições. Tente novamente em instantes.", {"retry_after": retry}
            )

    return _dep


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Limite global por IP (proteção geral contra abuso)."""

    def __init__(self, app, limit: int = 600, window_seconds: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window_seconds

    async def dispatch(self, request, call_next):
        if request.url.path in ("/health", "/ready"):
            return await call_next(request)
        ok, retry = hit(f"global:{client_ip(request)}", self.limit, self.window)
        if not ok:
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry)},
                content={"error": {"code": "rate_limited", "message": "Muitas requisições"}},
            )
        return await call_next(request)
