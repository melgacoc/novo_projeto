"""Tokens e hashes. Não existem senhas: login por Google ou código por e-mail."""
import hashlib
import hmac
import secrets
import string
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings

ALGORITHM = "HS256"


def now_utc() -> datetime:
    return datetime.now(UTC)


def hash_token(value: str) -> str:
    """Hash determinístico (HMAC-SHA256 com o SECRET_KEY) para guardar tokens e códigos."""
    return hmac.new(settings.secret_key.encode(), value.encode(), hashlib.sha256).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


def new_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def new_login_code() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(6))


def new_booking_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sem 0/O/1/I
    return "RJ-" + "".join(secrets.choice(alphabet) for _ in range(6))


def create_access_token(user_id: int, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": now_utc(),
        "exp": now_utc() + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "access":
        return None
    return payload
