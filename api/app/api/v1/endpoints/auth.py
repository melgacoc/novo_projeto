"""Autenticação. Fica desligada (409 auth_disabled) enquanto AUTH_ENABLED=false.

Sessão: access token curto no corpo da resposta (o frontend guarda em memória) + refresh token rotativo
em cookie httpOnly. Refresh e logout exigem o header X-CSRF-Token igual ao cookie `tur_csrf`."""
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Depends, Header, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.core.ratelimit import rate_limit
from app.core.redis import redis_client
from app.core.security import constant_time_equals, new_token
from app.models import Operator, OperatorMember, User
from app.schemas.booking import EmailCodeRequest, EmailCodeVerify
from app.services import auth_service, serializers

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "tur_refresh"
CSRF_COOKIE = "tur_csrf"
COOKIE_PATH = "/api/v1/auth"


def require_auth_enabled() -> None:
    if not settings.auth_enabled:
        raise AppError(409, "auth_disabled", "Login desligado neste ambiente (AUTH_ENABLED=false)")


def _set_session_cookies(response: Response, refresh_raw: str) -> str:
    csrf = new_token(24)
    max_age = settings.refresh_token_days * 86400
    response.set_cookie(REFRESH_COOKIE, refresh_raw, max_age=max_age, httponly=True,
                        secure=settings.is_production, samesite="lax", path=COOKIE_PATH)
    response.set_cookie(CSRF_COOKIE, csrf, max_age=max_age, httponly=False,
                        secure=settings.is_production, samesite="lax", path="/")
    return csrf


def _clear_cookies(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=COOKIE_PATH)
    response.delete_cookie(CSRF_COOKIE, path="/")


def _check_csrf(csrf_cookie: str | None, csrf_header: str | None) -> None:
    if not csrf_cookie or not csrf_header or not constant_time_equals(csrf_cookie, csrf_header):
        raise AppError(403, "csrf", "Falha na verificação CSRF")


def _session_body(db: Session, user: User, access: str) -> dict:
    ops = db.scalars(
        select(Operator).join(OperatorMember, OperatorMember.operator_id == Operator.id)
        .where(OperatorMember.user_id == user.id)
    ).all()
    return {"access_token": access, "token_type": "bearer", "user": serializers.user_me(user, list(ops))}


@router.post("/email/request-code", dependencies=[Depends(require_auth_enabled), Depends(rate_limit("login-code", 5, 600))])
def request_code(body: EmailCodeRequest, db: Session = Depends(get_db)):
    auth_service.request_email_code(db, body.email, body.locale)
    # resposta igual exista ou não a conta (não revela e-mails cadastrados)
    return {"message": "Se o e-mail for válido, enviamos um código."}


@router.post("/email/verify", dependencies=[Depends(require_auth_enabled), Depends(rate_limit("login-verify", 10, 600))])
def verify_code(body: EmailCodeVerify, response: Response, db: Session = Depends(get_db)):
    user = auth_service.verify_email_code(db, body.email, body.code, body.locale)
    access, refresh = auth_service.issue_session(db, user)
    _set_session_cookies(response, refresh)
    return _session_body(db, user, access)


@router.get("/google/start", dependencies=[Depends(require_auth_enabled), Depends(rate_limit("login-google", 20, 600))])
def google_start(next: str = "/"):
    state = new_token(24)
    safe_next = next if next.startswith("/") and not next.startswith("//") else "/"
    redis_client.setex(f"oauth:state:{state}", 600, safe_next)
    return RedirectResponse(auth_service.google_auth_url(state), status_code=302)


@router.get("/google/callback", dependencies=[Depends(require_auth_enabled)])
def google_callback(code: str | None = None, state: str | None = None, error: str | None = None,
                    db: Session = Depends(get_db)):
    front = settings.primary_frontend_url
    next_path = redis_client.getdel(f"oauth:state:{state}") if state else None
    if error or not code or not next_path:
        return RedirectResponse(f"{front}/auth/callback?{urlencode({'error': error or 'invalid_state'})}", 302)
    user = auth_service.google_user_from_code(db, code)
    _, refresh = auth_service.issue_session(db, user)
    response = RedirectResponse(f"{front}/auth/callback?{urlencode({'next': next_path})}", 302)
    _set_session_cookies(response, refresh)
    return response


@router.post("/refresh", dependencies=[Depends(require_auth_enabled), Depends(rate_limit("refresh", 60, 60))])
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    x_csrf_token: str | None = Header(default=None),
):
    _check_csrf(csrf_cookie, x_csrf_token)
    if not refresh_cookie:
        raise AppError(401, "invalid_session", "Sessão expirada. Entre novamente.")
    try:
        user, access, new_refresh = auth_service.rotate_refresh(db, refresh_cookie)
    except AppError:
        _clear_cookies(response)
        raise
    _set_session_cookies(response, new_refresh)
    return _session_body(db, user, access)


@router.post("/logout", dependencies=[Depends(require_auth_enabled)])
def logout(
    response: Response,
    db: Session = Depends(get_db),
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    x_csrf_token: str | None = Header(default=None),
):
    _check_csrf(csrf_cookie, x_csrf_token)
    if refresh_cookie:
        auth_service.revoke_refresh(db, refresh_cookie)
    _clear_cookies(response)
    return {"message": "ok"}


@router.post("/logout-all", dependencies=[Depends(require_auth_enabled)])
def logout_all(request: Request, response: Response, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    auth_service.revoke_all(db, user.id)
    _clear_cookies(response)
    return {"message": "ok"}
