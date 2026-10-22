"""Painel admin: operadoras (comissão individual), aprovação de passeios, reservas, repasses, configurações."""
from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_admin
from app.core.errors import bad_request, conflict, not_found
from app.core.pagination import PageParams, paginate
from app.core.security import hash_token, new_token, now_utc
from app.models import (
    AuditLog,
    Booking,
    Category,
    Operator,
    OperatorInvite,
    OperatorMember,
    Payment,
    Payout,
    Refund,
    Tour,
    User,
)
from app.models.operator import OPERATOR_STATUSES
from app.models.platform import DEFAULT_SETTINGS
from app.schemas.booking import AdminCancelIn
from app.schemas.tour import TourIn
from app.services import booking_service, email_service, payout_service, platform_settings, serializers, tour_service
from app.services.catalog_service import tour_text

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------
@router.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    now = now_utc()
    paid = Booking.status.in_(["confirmed", "completed", "no_show"])

    def window(days: int):
        row = db.execute(
            select(func.count(), func.coalesce(func.sum(Booking.total_cents), 0),
                   func.coalesce(func.sum(Booking.commission_cents), 0))
            .where(paid, Booking.confirmed_at >= now - timedelta(days=days))
        ).one()
        return {"bookings": row[0], "gmv_cents": int(row[1]), "commission_cents": int(row[2])}

    created_7d = db.scalar(select(func.count()).select_from(Booking).where(Booking.created_at >= now - timedelta(days=7))) or 0
    paid_7d = db.scalar(select(func.count()).select_from(Booking).where(Booking.paid_at >= now - timedelta(days=7))) or 0
    expired_7d = db.scalar(select(func.count()).select_from(Booking).where(
        Booking.status == "expired", Booking.created_at >= now - timedelta(days=7))) or 0
    refunds_30d = db.scalar(select(func.coalesce(func.sum(Refund.amount_cents), 0)).where(
        Refund.created_at >= now - timedelta(days=30))) or 0
    return {
        "last_7_days": window(7),
        "last_30_days": window(30),
        "funnel_7_days": {"holds": created_7d, "paid": paid_7d, "expired": expired_7d},
        "refunds_30d_cents": int(refunds_30d),
        "operators_by_status": dict(db.execute(select(Operator.status, func.count()).group_by(Operator.status)).all()),
        "tours_by_status": dict(db.execute(select(Tour.status, func.count()).group_by(Tour.status)).all()),
        "pending_review": db.scalar(select(func.count()).select_from(Tour).where(Tour.status == "pending_review")),
        "cancellations_by_operator": [
            {"operator": n, "count": c} for n, c in db.execute(
                select(Operator.public_name, Operator.cancellations_count)
                .where(Operator.cancellations_count > 0).order_by(Operator.cancellations_count.desc()).limit(10)
            ).all()
        ],
    }


# ---------------------------------------------------------------------------
# Operadoras
# ---------------------------------------------------------------------------
class OperatorIn(BaseModel):
    public_name: str = Field(min_length=2, max_length=120)
    trade_name: str = Field(min_length=2, max_length=160)
    legal_name: str = Field("", max_length=200)
    document: str = Field("", max_length=20)
    cadastur_number: str = Field("", max_length=40)
    contact_phone: str = Field("", max_length=20)
    contact_email: EmailStr | None = None
    notes: str = ""
    status: str = "active"

    @field_validator("status")
    @classmethod
    def _st(cls, v: str) -> str:
        if v not in OPERATOR_STATUSES:
            raise ValueError("Status inválido")
        return v


class OperatorPatch(BaseModel):
    public_name: str | None = Field(None, max_length=120)
    trade_name: str | None = Field(None, max_length=160)
    legal_name: str | None = None
    document: str | None = None
    cadastur_number: str | None = None
    contact_phone: str | None = None
    contact_email: EmailStr | None = None
    notes: str | None = None
    status: str | None = None
    # null explícito = volta para a comissão padrão
    commission_rate: Decimal | None = Field(None, ge=0, le=Decimal("0.9"))
    reset_commission: bool = False
    gateway_recipient_id: str | None = None

    @field_validator("status")
    @classmethod
    def _st(cls, v: str | None) -> str | None:
        if v is not None and v not in OPERATOR_STATUSES:
            raise ValueError("Status inválido")
        return v


class InviteIn(BaseModel):
    email: EmailStr


@router.get("/operators")
def list_operators(q: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Operator).order_by(Operator.public_name)
    if q:
        stmt = stmt.where(or_(Operator.public_name.ilike(f"%{q}%"), Operator.trade_name.ilike(f"%{q}%")))
    default = platform_settings.default_commission_rate(db)
    ops = db.scalars(stmt).all()
    counts = dict(db.execute(select(Tour.operator_id, func.count()).group_by(Tour.operator_id)).all())
    return [{**serializers.operator_admin(o, default), "tours_count": counts.get(o.id, 0)} for o in ops]


@router.post("/operators", status_code=201)
def create_operator(body: OperatorIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    data = body.model_dump()
    data["contact_email"] = data["contact_email"] or ""
    o = Operator(**data)
    db.add(o)
    db.flush()
    audit(db, admin.id, "operator", o.id, "create", None, {"public_name": o.public_name})
    db.commit()
    return serializers.operator_admin(o, platform_settings.default_commission_rate(db))


@router.get("/operators/{operator_id}")
def get_operator(operator_id: int, db: Session = Depends(get_db)):
    o = db.get(Operator, operator_id)
    if not o:
        raise not_found("Operadora")
    members = db.execute(select(OperatorMember, User).join(User, User.id == OperatorMember.user_id)
                         .where(OperatorMember.operator_id == o.id)).all()
    invites = db.scalars(select(OperatorInvite).where(OperatorInvite.operator_id == o.id)
                         .order_by(OperatorInvite.id.desc())).all()
    tours = db.scalars(select(Tour).where(Tour.operator_id == o.id).order_by(Tour.id.desc())).all()
    return {
        **serializers.operator_admin(o, platform_settings.default_commission_rate(db)),
        "members": [{"user_id": u.id, "email": u.email, "name": u.name, "role": m.role} for m, u in members],
        "invites": [{"id": i.id, "email": i.email, "expires_at": i.expires_at.isoformat(),
                     "accepted_at": i.accepted_at.isoformat() if i.accepted_at else None} for i in invites],
        "tours": [{"id": t.id, "title": tour_text(t, "pt").title, "status": t.status, "slug": t.slug} for t in tours],
    }


@router.patch("/operators/{operator_id}")
def patch_operator(operator_id: int, body: OperatorPatch, admin: User = Depends(require_admin),
                   db: Session = Depends(get_db)):
    o = db.get(Operator, operator_id)
    if not o:
        raise not_found("Operadora")
    old = serializers.operator_admin(o, platform_settings.default_commission_rate(db))
    data = body.model_dump(exclude_unset=True)
    reset = data.pop("reset_commission", False)
    for k, v in data.items():
        if k == "contact_email" and v is None:
            continue
        setattr(o, k, v)
    if reset:
        o.commission_rate = None
    new = serializers.operator_admin(o, platform_settings.default_commission_rate(db))
    changed = {k: new[k] for k in new if new[k] != old.get(k)}
    audit(db, admin.id, "operator", o.id, "update", {k: old.get(k) for k in changed}, changed)
    db.commit()
    return get_operator(operator_id, db)


@router.post("/operators/{operator_id}/invites", status_code=201)
def invite(operator_id: int, body: InviteIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    o = db.get(Operator, operator_id)
    if not o:
        raise not_found("Operadora")
    token = new_token()
    inv = OperatorInvite(operator_id=o.id, email=str(body.email).lower(), token_hash=hash_token(token),
                         expires_at=now_utc() + timedelta(days=7))
    db.add(inv)
    audit(db, admin.id, "operator", o.id, "invite", None, {"email": inv.email})
    db.commit()
    link = f"{settings.primary_frontend_url}/painel/convite?token={token}"
    email_service.enqueue_email(
        inv.email, f"Convite para vender seus passeios em {settings.app_name}",
        f"<p>Você foi convidado(a) para gerenciar <b>{o.public_name}</b> em {settings.app_name}.</p>"
        f"<p><a href=\"{link}\">Aceitar convite</a> (válido por 7 dias).</p>",
    )
    # o link volta na resposta para o admin poder enviar por WhatsApp
    return {"id": inv.id, "email": inv.email, "link": link, "expires_at": inv.expires_at.isoformat()}


# ---------------------------------------------------------------------------
# Passeios (aprovação e edição concierge)
# ---------------------------------------------------------------------------
class ReviewIn(BaseModel):
    notes: str = Field("", max_length=2000)


@router.get("/tours")
def list_tours(status: str | None = None, operator_id: int | None = None, q: str | None = None,
               page: PageParams = Depends(), db: Session = Depends(get_db)):
    stmt = select(Tour).order_by(Tour.updated_at.desc())
    if status:
        stmt = stmt.where(Tour.status == status)
    if operator_id:
        stmt = stmt.where(Tour.operator_id == operator_id)
    if q:
        stmt = stmt.where(Tour.slug.ilike(f"%{q}%"))
    rows, total = paginate(db, stmt, page)
    ops = {o.id: o for o in db.scalars(select(Operator)).all()}
    return {
        "items": [{
            "id": t.id, "slug": t.slug, "title": tour_text(t, "pt").title, "status": t.status,
            "operator_id": t.operator_id, "operator_name": ops[t.operator_id].public_name,
            "from_price_cents": t.from_price_cents, "photo": t.photos[0].url if t.photos else None,
            "problems": tour_service.publication_problems(t), "flags": tour_service.contact_flags(t),
            "updated_at": t.updated_at.isoformat(),
        } for t in rows],
        "total": total, "page": page.page, "page_size": page.page_size,
    }


def _tour(db: Session, tour_id: int) -> Tour:
    t = db.get(Tour, tour_id)
    if not t:
        raise not_found("Passeio")
    return t


@router.get("/tours/{tour_id}")
def get_tour(tour_id: int, db: Session = Depends(get_db)):
    t = _tour(db, tour_id)
    data = serializers.tour_full(t, db)
    data["problems"] = tour_service.publication_problems(t)
    data["contact_flags"] = tour_service.contact_flags(t)
    data["operator_name"] = db.get(Operator, t.operator_id).public_name
    return data


@router.put("/tours/{tour_id}")
def update_tour(tour_id: int, body: TourIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    tour_service.update(db, _tour(db, tour_id), body, admin.id)
    return get_tour(tour_id, db)


@router.post("/operators/{operator_id}/tours", status_code=201)
def create_tour_for_operator(operator_id: int, body: TourIn, admin: User = Depends(require_admin),
                             db: Session = Depends(get_db)):
    if not db.get(Operator, operator_id):
        raise not_found("Operadora")
    t = tour_service.create(db, operator_id, body, admin.id)
    return get_tour(t.id, db)


@router.post("/tours/{tour_id}/approve")
def approve(tour_id: int, body: ReviewIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    tour_service.set_status(db, _tour(db, tour_id), "published", admin.id, body.notes)
    return get_tour(tour_id, db)


@router.post("/tours/{tour_id}/reject")
def reject(tour_id: int, body: ReviewIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if not body.notes:
        raise bad_request("notes_required", "Explique o motivo da rejeição")
    tour_service.set_status(db, _tour(db, tour_id), "rejected", admin.id, body.notes)
    return get_tour(tour_id, db)


@router.post("/tours/{tour_id}/pause")
def pause(tour_id: int, body: ReviewIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    tour_service.set_status(db, _tour(db, tour_id), "paused", admin.id, body.notes)
    return get_tour(tour_id, db)


# ---------------------------------------------------------------------------
# Categorias
# ---------------------------------------------------------------------------
class CategoryIn(BaseModel):
    slug: str = Field(min_length=2, max_length=60, pattern="^[a-z0-9-]+$")
    name_pt: str = Field(min_length=2, max_length=80)
    name_es: str = Field(min_length=2, max_length=80)
    name_en: str = Field(min_length=2, max_length=80)
    icon: str = Field("map-pin", max_length=40)
    position: int = 0


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    return [serializers.category(c, "pt") for c in db.scalars(select(Category).order_by(Category.position)).all()]


@router.post("/categories", status_code=201)
def create_category(body: CategoryIn, db: Session = Depends(get_db)):
    if db.scalar(select(Category).where(Category.slug == body.slug)):
        raise conflict("duplicate", "Já existe uma categoria com este slug")
    c = Category(**body.model_dump())
    db.add(c)
    db.commit()
    return serializers.category(c, "pt")


@router.put("/categories/{category_id}")
def update_category(category_id: int, body: CategoryIn, db: Session = Depends(get_db)):
    c = db.get(Category, category_id)
    if not c:
        raise not_found("Categoria")
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    db.commit()
    return serializers.category(c, "pt")


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    c = db.get(Category, category_id)
    if not c:
        raise not_found("Categoria")
    if db.scalar(select(Tour.id).where(Tour.category_id == c.id).limit(1)):
        raise conflict("in_use", "Categoria em uso por passeios")
    db.delete(c)
    db.commit()


# ---------------------------------------------------------------------------
# Reservas
# ---------------------------------------------------------------------------
@router.get("/bookings")
def list_bookings(status: str | None = None, operator_id: int | None = None, q: str | None = None,
                  page: PageParams = Depends(), db: Session = Depends(get_db)):
    stmt = select(Booking).where(Booking.status != "expired").order_by(Booking.id.desc())
    if status:
        stmt = stmt.where(Booking.status == status)
    if operator_id:
        stmt = stmt.where(Booking.operator_id == operator_id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Booking.code.ilike(like), Booking.contact_email.ilike(like),
                              Booking.contact_name.ilike(like)))
    rows, total = paginate(db, stmt, page)
    return {"items": [serializers.booking(b, db, audience="admin") for b in rows], "total": total,
            "page": page.page, "page_size": page.page_size}


def _booking(db: Session, code: str) -> Booking:
    b = db.scalar(select(Booking).where(Booking.code == code.upper()))
    if not b:
        raise not_found("Reserva")
    return b


@router.get("/bookings/{code}")
def get_booking(code: str, db: Session = Depends(get_db)):
    b = _booking(db, code)
    data = serializers.booking(b, db, audience="admin")
    data["refunds"] = [{"amount_cents": r.amount_cents, "reason": r.reason, "status": r.status,
                        "created_at": r.created_at.isoformat()}
                       for r in db.scalars(select(Refund).where(Refund.booking_id == b.id)).all()]
    return data


@router.post("/bookings/{code}/cancel")
def cancel_booking(code: str, body: AdminCancelIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    b = booking_service.cancel_booking(db, _booking(db, code), by="admin", reason=body.reason or "admin",
                                       actor_id=admin.id, refund_cents=body.refund_cents)
    return get_booking(b.code, db)


# ---------------------------------------------------------------------------
# Repasses
# ---------------------------------------------------------------------------
class MarkPaidIn(BaseModel):
    transfer_id: str | None = Field(None, max_length=120)
    notes: str = Field("", max_length=1000)


def _payout(p: Payout, ops: dict[int, Operator]) -> dict:
    return {"id": p.id, "operator_id": p.operator_id, "operator_name": ops[p.operator_id].public_name,
            "period_start": p.period_start.isoformat(), "period_end": p.period_end.isoformat(),
            "amount_cents": p.amount_cents, "status": p.status, "items_count": len(p.items),
            "paid_at": p.paid_at.isoformat() if p.paid_at else None, "transfer_id": p.gateway_transfer_id,
            "notes": p.notes, "created_at": p.created_at.isoformat()}


@router.get("/payouts")
def list_payouts(status: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Payout).order_by(Payout.id.desc())
    if status:
        stmt = stmt.where(Payout.status == status)
    ops = {o.id: o for o in db.scalars(select(Operator)).all()}
    eligible = payout_service.eligible_bookings(db)
    preview: dict[int, int] = {}
    for b in eligible:
        preview[b.operator_id] = preview.get(b.operator_id, 0) + b.operator_amount_cents
    return {
        "items": [_payout(p, ops) for p in db.scalars(stmt).all()],
        "eligible": [{"operator_id": k, "operator_name": ops[k].public_name, "amount_cents": v}
                     for k, v in preview.items()],
        "payout_delay_days": platform_settings.payout_delay_days(db),
    }


@router.post("/payouts/generate")
def generate_payouts(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    payouts = payout_service.generate(db, admin.id)
    ops = {o.id: o for o in db.scalars(select(Operator)).all()}
    return [_payout(p, ops) for p in payouts]


@router.post("/payouts/{payout_id}/mark-paid")
def mark_paid(payout_id: int, body: MarkPaidIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    p = db.get(Payout, payout_id)
    if not p:
        raise not_found("Repasse")
    payout_service.mark_paid(db, p, admin.id, body.transfer_id, body.notes)
    ops = {o.id: o for o in db.scalars(select(Operator)).all()}
    return _payout(p, ops)


# ---------------------------------------------------------------------------
# Configurações, usuários e auditoria
# ---------------------------------------------------------------------------
class SettingsPatch(BaseModel):
    default_commission_rate: Decimal | None = Field(None, ge=0, le=Decimal("0.9"))
    hold_minutes: int | None = Field(None, ge=5, le=60)
    payout_delay_days: int | None = Field(None, ge=0, le=60)
    low_availability_min_seats: int | None = Field(None, ge=0, le=50)


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    return platform_settings.get_all(db)


@router.patch("/settings")
def patch_settings(body: SettingsPatch, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    old = platform_settings.get_all(db)
    for k, v in body.model_dump(exclude_none=True).items():
        if k in DEFAULT_SETTINGS:
            platform_settings.set_setting(db, k, str(v))
    new = platform_settings.get_all(db)
    audit(db, admin.id, "settings", "platform", "update", old, new)
    db.commit()
    return new


class UserPatch(BaseModel):
    role: str | None = None
    is_active: bool | None = None

    @field_validator("role")
    @classmethod
    def _r(cls, v: str | None) -> str | None:
        if v is not None and v not in ("tourist", "operator", "admin"):
            raise ValueError("Papel inválido")
        return v


class MemberIn(BaseModel):
    email: EmailStr


@router.get("/users")
def list_users(role: str | None = None, q: str | None = None, page: PageParams = Depends(),
               db: Session = Depends(get_db)):
    stmt = select(User).order_by(User.id.desc())
    if role:
        stmt = stmt.where(User.role == role)
    if q:
        stmt = stmt.where(or_(User.email.ilike(f"%{q}%"), User.name.ilike(f"%{q}%")))
    rows, total = paginate(db, stmt, page)
    return {"items": [{"id": u.id, "email": u.email, "name": u.name, "role": u.role, "is_active": u.is_active,
                       "is_dev_user": u.is_dev_user, "created_at": u.created_at.isoformat()} for u in rows],
            "total": total, "page": page.page, "page_size": page.page_size}


@router.patch("/users/{user_id}")
def patch_user(user_id: int, body: UserPatch, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise not_found("Usuário")
    if u.id == admin.id and (body.role not in (None, "admin") or body.is_active is False):
        raise conflict("self_demotion", "Você não pode rebaixar ou desativar a si mesmo")
    old = {"role": u.role, "is_active": u.is_active}
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(u, k, v)
    audit(db, admin.id, "user", u.id, "update", old, body.model_dump(exclude_none=True))
    db.commit()
    return {"id": u.id, "email": u.email, "role": u.role, "is_active": u.is_active}


@router.post("/operators/{operator_id}/members", status_code=201)
def add_member(operator_id: int, body: MemberIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Vincula um usuário existente (pelo e-mail) a uma operadora."""
    o = db.get(Operator, operator_id)
    u = db.scalar(select(User).where(User.email == str(body.email).lower()))
    if not o or not u:
        raise not_found("Operadora ou usuário")
    if not db.scalar(select(OperatorMember).where(OperatorMember.operator_id == o.id, OperatorMember.user_id == u.id)):
        db.add(OperatorMember(operator_id=o.id, user_id=u.id, role="owner"))
    if u.role == "tourist":
        u.role = "operator"
    audit(db, admin.id, "operator", o.id, "add_member", None, {"email": u.email})
    db.commit()
    return {"ok": True}


@router.get("/audit-logs")
def audit_logs(entity: str | None = None, entity_id: str | None = None, page: PageParams = Depends(),
               db: Session = Depends(get_db)):
    stmt = select(AuditLog).order_by(AuditLog.id.desc())
    if entity:
        stmt = stmt.where(AuditLog.entity == entity)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    rows, total = paginate(db, stmt, page)
    users = {u.id: u.email for u in db.scalars(select(User).where(User.id.in_({r.user_id for r in rows if r.user_id}))).all()}
    return {"items": [{"id": r.id, "user": users.get(r.user_id), "entity": r.entity, "entity_id": r.entity_id,
                       "action": r.action, "old": r.old_values, "new": r.new_values,
                       "created_at": r.created_at.isoformat()} for r in rows],
            "total": total, "page": page.page, "page_size": page.page_size}


@router.get("/payments")
def payments(page: PageParams = Depends(), db: Session = Depends(get_db)):
    rows, total = paginate(db, select(Payment).order_by(Payment.id.desc()), page)
    return {"items": [serializers.payment(p) for p in rows], "total": total, "page": page.page,
            "page_size": page.page_size}
