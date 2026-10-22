"""Login por código de e-mail e Google, sessões com refresh token rotativo."""
from datetime import timedelta
from urllib.parse import urlencode

import httpx
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import (
    constant_time_equals,
    create_access_token,
    hash_token,
    new_login_code,
    new_token,
    now_utc,
)
from app.models import EmailLoginCode, RefreshToken, User
from app.services import email_service

CODE_TTL_MINUTES = 10
CODE_MAX_ATTEMPTS = 5


def _normalize_email(email: str) -> str:
    return email.strip().lower()


# ---------------------------------------------------------------------------
# Código por e-mail
# ---------------------------------------------------------------------------
def request_email_code(db: Session, email: str, locale: str) -> None:
    email = _normalize_email(email)
    # invalida códigos anteriores ainda abertos
    db.execute(
        update(EmailLoginCode)
        .where(EmailLoginCode.email == email, EmailLoginCode.used_at.is_(None))
        .values(used_at=now_utc())
    )
    code = new_login_code()
    db.add(
        EmailLoginCode(
            email=email, code_hash=hash_token(code), expires_at=now_utc() + timedelta(minutes=CODE_TTL_MINUTES)
        )
    )
    db.commit()
    subject, html = email_service.render("login_code", locale, code=code)
    email_service.enqueue_email(email, subject, html)


def verify_email_code(db: Session, email: str, code: str, locale: str) -> User:
    email = _normalize_email(email)
    row = db.scalar(
        select(EmailLoginCode)
        .where(EmailLoginCode.email == email, EmailLoginCode.used_at.is_(None))
        .order_by(EmailLoginCode.id.desc())
        .with_for_update()
    )
    invalid = AppError(400, "invalid_code", "Código inválido ou expirado")
    if not row or row.expires_at < now_utc() or row.attempts >= CODE_MAX_ATTEMPTS:
        raise invalid
    row.attempts += 1
    if not constant_time_equals(row.code_hash, hash_token(code.strip())):
        db.commit()
        raise invalid
    row.used_at = now_utc()
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        user = User(email=email, name="", role="tourist", locale=locale, is_active=True)
        db.add(user)
    if not user.is_active:
        raise AppError(403, "inactive", "Usuário desativado")
    db.commit()
    return user


# ---------------------------------------------------------------------------
# Google (fluxo authorization code, todo no backend)
# ---------------------------------------------------------------------------
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def google_auth_url(state: str) -> str:
    if not settings.google_configured:
        raise AppError(503, "google_not_configured", "Login com Google não configurado")
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def google_user_from_code(db: Session, code: str) -> User:
    token = httpx.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    if token.status_code != 200:
        raise AppError(400, "google_error", "Falha ao autenticar com o Google")
    info = httpx.get(
        GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {token.json()['access_token']}"}, timeout=10
    ).json()
    if not info.get("email_verified"):
        raise AppError(400, "google_email_unverified", "E-mail do Google não verificado")
    email = _normalize_email(info["email"])
    user = db.scalar(select(User).where(User.google_sub == info["sub"]))
    if not user:
        user = db.scalar(select(User).where(User.email == email))
        if user:
            user.google_sub = info["sub"]
        else:
            user = User(email=email, name=info.get("name", ""), role="tourist", google_sub=info["sub"], is_active=True)
            db.add(user)
    if not user.name and info.get("name"):
        user.name = info["name"]
    if not user.is_active:
        raise AppError(403, "inactive", "Usuário desativado")
    db.commit()
    return user


# ---------------------------------------------------------------------------
# Sessão
# ---------------------------------------------------------------------------
def issue_session(db: Session, user: User, family: str | None = None) -> tuple[str, str]:
    """Cria access token + refresh token. Retorna (access, refresh em texto puro)."""
    raw = new_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            family=family or new_token(16),
            expires_at=now_utc() + timedelta(days=settings.refresh_token_days),
        )
    )
    db.commit()
    return create_access_token(user.id, user.role), raw


def rotate_refresh(db: Session, raw: str) -> tuple[User, str, str]:
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)).with_for_update())
    invalid = AppError(401, "invalid_session", "Sessão expirada. Entre novamente.")
    if not row:
        raise invalid
    if row.revoked_at is not None:
        # reuso de token já trocado: possível roubo. Revoga toda a família.
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.family == row.family, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now_utc())
        )
        db.commit()
        raise invalid
    if row.expires_at < now_utc():
        raise invalid
    user = db.get(User, row.user_id)
    if not user or not user.is_active:
        raise invalid
    row.revoked_at = now_utc()
    access, new_raw = issue_session(db, user, family=row.family)
    return user, access, new_raw


def revoke_refresh(db: Session, raw: str) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == hash_token(raw), RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now_utc())
    )
    db.commit()


def revoke_all(db: Session, user_id: int) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now_utc())
    )
    db.commit()
