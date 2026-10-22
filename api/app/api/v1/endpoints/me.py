from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Operator, OperatorMember, User
from app.schemas.booking import MePatch
from app.services import serializers

router = APIRouter(prefix="/me", tags=["me"])


def _ops(db: Session, user: User) -> list[Operator]:
    if user.role == "admin":
        return list(db.scalars(select(Operator).order_by(Operator.public_name)).all())
    return list(
        db.scalars(
            select(Operator).join(OperatorMember, OperatorMember.operator_id == Operator.id)
            .where(OperatorMember.user_id == user.id).order_by(Operator.public_name)
        ).all()
    )


@router.get("")
def get_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return serializers.user_me(user, _ops(db, user))


@router.patch("")
def patch_me(body: MePatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.name is not None:
        user.name = body.name.strip()
    if body.phone is not None:
        user.phone_e164 = body.phone
    if body.locale is not None:
        user.locale = body.locale
    db.commit()
    return serializers.user_me(user, _ops(db, user))
