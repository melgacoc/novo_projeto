"""Dependências de autenticação e autorização.

Com AUTH_ENABLED=true: exige `Authorization: Bearer <access token>`.
Com AUTH_ENABLED=false (desenvolvimento): usa um usuário fixo por papel, escolhido pelo header
`X-Dev-User-Role` (tourist | operator | admin). As regras de papel e de escopo por operadora são
aplicadas igualmente nos dois modos.
"""
import logging
from dataclasses import dataclass

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import AppError, forbidden
from app.core.security import decode_access_token
from app.models import Operator, OperatorMember, User

log = logging.getLogger("app.auth")

DEV_EMAILS = {
    "tourist": "turista.dev@tur.local",
    "operator": "operadora.dev@tur.local",
    "admin": "admin.dev@tur.local",
}


def _unauthorized() -> AppError:
    return AppError(401, "unauthorized", "Faça login para continuar")


def _dev_user(db: Session, role: str | None) -> User:
    role = role if role in DEV_EMAILS else "tourist"
    user = db.scalar(select(User).where(User.email == DEV_EMAILS[role]))
    if not user:
        raise AppError(500, "dev_user_missing", "Usuários de desenvolvimento não encontrados. Rode o seed.")
    return user


def get_optional_user(
    request: Request,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    x_dev_user_role: str | None = Header(default=None),
) -> User | None:
    if not settings.auth_enabled:
        if not x_dev_user_role:
            return None
        user = _dev_user(db, x_dev_user_role)
        request.state.user_id = user.id
        return user

    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    payload = decode_access_token(authorization.split(" ", 1)[1])
    if not payload:
        return None
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active or user.is_dev_user:
        return None
    request.state.user_id = user.id
    return user


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise _unauthorized()
    return user


def require_role(*roles: str):
    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise forbidden()
        return user

    return _dep


require_admin = require_role("admin")


@dataclass
class OperatorContext:
    user: User
    operator: Operator


def get_operator_context(
    user: User = Depends(require_role("operator", "admin")),
    db: Session = Depends(get_db),
    x_operator_id: str | None = Header(default=None),
) -> OperatorContext:
    """Operadora em que o usuário está atuando. Um usuário pode pertencer a mais de uma:
    escolhe com o header `X-Operator-Id`; sem ele, usa a primeira. Admin pode atuar em qualquer uma."""
    operator: Operator | None = None
    if x_operator_id:
        if not x_operator_id.isdigit():
            raise forbidden("Operadora inválida")
        operator = db.get(Operator, int(x_operator_id))
        if not operator:
            raise forbidden("Operadora inválida")
        if user.role != "admin":
            member = db.scalar(
                select(OperatorMember).where(
                    OperatorMember.operator_id == operator.id, OperatorMember.user_id == user.id
                )
            )
            if not member:
                raise forbidden("Você não pertence a esta operadora")
    else:
        operator = db.scalar(
            select(Operator)
            .join(OperatorMember, OperatorMember.operator_id == Operator.id)
            .where(OperatorMember.user_id == user.id)
            .order_by(Operator.id)
        )
        if not operator:
            raise forbidden("Nenhuma operadora vinculada ao seu usuário")
    if operator.status == "suspended":
        raise forbidden("Operadora suspensa")
    return OperatorContext(user=user, operator=operator)
