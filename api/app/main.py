import logging
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse

from app.api.v1.endpoints import admin, auth, bookings, me, operator, public
from app.core.config import settings
from app.core.database import engine
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging
from app.core.middleware import BodySizeLimitMiddleware, RequestIdMiddleware, SecurityHeadersMiddleware
from app.core.ratelimit import RateLimitMiddleware
from app.core.redis import redis_client

setup_logging()
log = logging.getLogger("app")

if not settings.auth_enabled:
    log.warning("AUTH_ENABLED=false: login desligado, usuários de desenvolvimento ativos")

app = FastAPI(
    title=f"{settings.app_name} API",
    description="Marketplace de passeios. Ver spec.md na raiz do repositório.",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
    openapi_url=None if settings.is_production else "/openapi.json",
)
register_error_handlers(app)

# ordem: o último adicionado é o mais externo
app.add_middleware(RateLimitMiddleware, limit=600, window_seconds=60)
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_urls,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Operator-Id", "X-Dev-User-Role",
                   "X-Request-ID", "Accept-Language"],
    expose_headers=["X-Request-ID"],
)
if settings.allowed_host_list and settings.app_env != "test":
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_host_list)

api = APIRouter(prefix="/api/v1")
for r in (public.router, auth.router, me.router, bookings.router, operator.router, admin.router):
    api.include_router(r)
app.include_router(api)

if not settings.storage_configured:
    Path(settings.media_dir).mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}


@app.get("/ready", include_in_schema=False)
def ready():
    checks = {}
    try:
        with engine.connect() as conn:
            conn.execute(text("select 1"))
        checks["db"] = "ok"
    except Exception:  # noqa: BLE001
        checks["db"] = "error"
    try:
        redis_client.ping()
        checks["redis"] = "ok"
    except Exception:  # noqa: BLE001
        checks["redis"] = "error"
    ok = all(v == "ok" for v in checks.values())
    return JSONResponse(status_code=200 if ok else 503, content={"status": "ok" if ok else "degraded", **checks})
