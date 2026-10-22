"""Painel da operadora: só enxerga os dados da própria operadora (escopo via OperatorContext)."""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.database import get_db
from app.core.deps import OperatorContext, get_current_user, get_operator_context
from app.core.errors import bad_request, conflict, not_found
from app.core.pagination import PageParams, paginate
from app.core.security import hash_token, now_utc
from app.models import Booking, Departure, OperatorInvite, OperatorMember, Payout, Tour, TourSchedule, User
from app.schemas.tour import CancelDepartureIn, DepartureIn, DeparturePatch, ScheduleIn, TourIn
from app.services import booking_service, payout_service, schedule_service, serializers, tour_service
from app.services.schedule_service import TZ

router = APIRouter(prefix="/operator", tags=["operator"])


class ProfilePatch(BaseModel):
    trade_name: str | None = Field(None, max_length=160)
    legal_name: str | None = Field(None, max_length=200)
    document: str | None = Field(None, max_length=20)
    cadastur_number: str | None = Field(None, max_length=40)
    contact_phone: str | None = Field(None, max_length=20)
    contact_email: EmailStr | None = None


class InviteAccept(BaseModel):
    token: str


def _tour(db: Session, ctx: OperatorContext, tour_id: int) -> Tour:
    tour = db.get(Tour, tour_id)
    if not tour or tour.operator_id != ctx.operator.id:
        raise not_found("Passeio")
    return tour


def _departure(db: Session, ctx: OperatorContext, dep_id: int) -> Departure:
    dep = db.get(Departure, dep_id)
    if not dep:
        raise not_found("Saída")
    _tour(db, ctx, dep.tour_id)
    return dep


def _booking(db: Session, ctx: OperatorContext, code: str) -> Booking:
    b = db.scalar(select(Booking).where(Booking.code == code.upper()))
    if not b or b.operator_id != ctx.operator.id:
        raise not_found("Reserva")
    return b


# ---------------------------------------------------------------------------
# Convite e perfil
# ---------------------------------------------------------------------------
@router.post("/invites/accept")
def accept_invite(body: InviteAccept, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    inv = db.scalar(select(OperatorInvite).where(OperatorInvite.token_hash == hash_token(body.token)))
    if not inv or inv.accepted_at or inv.expires_at < now_utc():
        raise bad_request("invalid_invite", "Convite inválido ou expirado")
    exists = db.scalar(select(OperatorMember).where(OperatorMember.operator_id == inv.operator_id,
                                                    OperatorMember.user_id == user.id))
    if not exists:
        db.add(OperatorMember(operator_id=inv.operator_id, user_id=user.id, role="owner"))
    if user.role == "tourist":
        user.role = "operator"
    inv.accepted_at = now_utc()
    audit(db, user.id, "operator", inv.operator_id, "invite_accepted")
    db.commit()
    return {"operator_id": inv.operator_id}


@router.get("/profile")
def profile(ctx: OperatorContext = Depends(get_operator_context), db: Session = Depends(get_db)):
    o = ctx.operator
    return {"id": o.id, "public_name": o.public_name, "trade_name": o.trade_name, "legal_name": o.legal_name,
            "document": o.document, "cadastur_number": o.cadastur_number, "status": o.status,
            "contact_phone": o.contact_phone, "contact_email": o.contact_email,
            "commission_rate": float(booking_service.commission_rate_for(db, o))}


@router.patch("/profile")
def patch_profile(body: ProfilePatch, ctx: OperatorContext = Depends(get_operator_context),
                  db: Session = Depends(get_db)):
    o = ctx.operator
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(o, k, v)
    audit(db, ctx.user.id, "operator", o.id, "profile_update", None, body.model_dump(exclude_none=True))
    db.commit()
    return profile(ctx, db)


@router.get("/dashboard")
def dashboard(ctx: OperatorContext = Depends(get_operator_context), db: Session = Depends(get_db)):
    now = now_utc()
    deps = db.scalars(
        select(Departure).join(Tour, Tour.id == Departure.tour_id)
        .where(Tour.operator_id == ctx.operator.id, Departure.starts_at >= now,
               Departure.starts_at < now + timedelta(days=2), Departure.seats_booked > 0)
        .order_by(Departure.starts_at)
    ).all()
    titles = {t.id: tour_service_title(t) for t in db.scalars(select(Tour).where(Tour.operator_id == ctx.operator.id)).all()}
    tours_by_status = dict(db.execute(
        select(Tour.status, func.count()).where(Tour.operator_id == ctx.operator.id).group_by(Tour.status)
    ).all())
    month_start = datetime.now(TZ).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month = db.execute(
        select(func.count(), func.coalesce(func.sum(Booking.operator_amount_cents), 0))
        .where(Booking.operator_id == ctx.operator.id, Booking.status.in_(["confirmed", "completed", "no_show"]),
               Booking.confirmed_at >= month_start)
    ).one()
    return {
        "operator": {"id": ctx.operator.id, "public_name": ctx.operator.public_name, "status": ctx.operator.status},
        "upcoming": [{**serializers.departure_operator(d), "title": titles.get(d.tour_id, "")} for d in deps],
        "tours_by_status": tours_by_status,
        "month_bookings": month[0],
        "month_amount_cents": int(month[1]),
        "pending_payout_cents": payout_service.pending_balance(db, ctx.operator.id),
        "upcoming_amount_cents": payout_service.upcoming_balance(db, ctx.operator.id),
    }


def tour_service_title(tour: Tour) -> str:
    from app.services.catalog_service import tour_text

    return tour_text(tour, "pt").title


# ---------------------------------------------------------------------------
# Passeios
# ---------------------------------------------------------------------------
@router.get("/tours")
def list_tours(ctx: OperatorContext = Depends(get_operator_context), db: Session = Depends(get_db)):
    tours = db.scalars(select(Tour).where(Tour.operator_id == ctx.operator.id).order_by(Tour.id.desc())).all()
    return [
        {"id": t.id, "slug": t.slug, "title": tour_service_title(t), "status": t.status,
         "from_price_cents": t.from_price_cents, "photo": t.photos[0].url if t.photos else None,
         "problems": tour_service.publication_problems(t), "updated_at": t.updated_at.isoformat()}
        for t in tours
    ]


@router.post("/tours", status_code=201)
def create_tour(body: TourIn, ctx: OperatorContext = Depends(get_operator_context), db: Session = Depends(get_db)):
    tour = tour_service.create(db, ctx.operator.id, body, ctx.user.id)
    return serializers.tour_full(tour, db)


@router.get("/tours/{tour_id}")
def get_tour(tour_id: int, ctx: OperatorContext = Depends(get_operator_context), db: Session = Depends(get_db)):
    tour = _tour(db, ctx, tour_id)
    data = serializers.tour_full(tour, db)
    data["problems"] = tour_service.publication_problems(tour)
    data["contact_flags"] = tour_service.contact_flags(tour)
    return data


@router.put("/tours/{tour_id}")
def update_tour(tour_id: int, body: TourIn, ctx: OperatorContext = Depends(get_operator_context),
                db: Session = Depends(get_db)):
    tour = _tour(db, ctx, tour_id)
    tour_service.update(db, tour, body, ctx.user.id)
    return get_tour(tour_id, ctx, db)


@router.delete("/tours/{tour_id}", status_code=204)
def delete_tour(tour_id: int, ctx: OperatorContext = Depends(get_operator_context), db: Session = Depends(get_db)):
    tour = _tour(db, ctx, tour_id)
    if tour.status not in ("draft", "rejected"):
        raise conflict("not_deletable", "Só rascunhos podem ser excluídos; pause o passeio publicado")
    if db.scalar(select(Booking.id).where(Booking.tour_id == tour.id).limit(1)):
        raise conflict("has_bookings", "Passeio com reservas não pode ser excluído")
    for p in list(tour.photos):
        tour_service.storage.delete(p.storage_key)
    db.delete(tour)
    db.commit()


@router.post("/tours/{tour_id}/submit")
def submit_tour(tour_id: int, ctx: OperatorContext = Depends(get_operator_context), db: Session = Depends(get_db)):
    tour = _tour(db, ctx, tour_id)
    has_schedule = db.scalar(select(func.count()).select_from(TourSchedule).where(TourSchedule.tour_id == tour.id)) > 0 \
        or db.scalar(select(func.count()).select_from(Departure).where(Departure.tour_id == tour.id)) > 0
    tour_service.submit(db, tour, has_schedule, ctx.user.id)
    return get_tour(tour_id, ctx, db)


@router.post("/tours/{tour_id}/pause")
def pause_tour(tour_id: int, ctx: OperatorContext = Depends(get_operator_context), db: Session = Depends(get_db)):
    tour = _tour(db, ctx, tour_id)
    if tour.status != "published":
        raise conflict("invalid_status", "Só passeios publicados podem ser pausados")
    tour_service.set_status(db, tour, "paused", ctx.user.id)
    return get_tour(tour_id, ctx, db)


@router.post("/tours/{tour_id}/photos", status_code=201)
async def upload_photo(tour_id: int, file: UploadFile = File(...), alt: str = Form(""),
                       ctx: OperatorContext = Depends(get_operator_context), db: Session = Depends(get_db)):
    tour = _tour(db, ctx, tour_id)
    content = await file.read(5 * 1024 * 1024 + 1)
    photo = tour_service.add_photo(db, tour, content, alt)
    return {"id": photo.id, "url": photo.url, "position": photo.position}


@router.delete("/tours/{tour_id}/photos/{photo_id}", status_code=204)
def delete_photo(tour_id: int, photo_id: int, ctx: OperatorContext = Depends(get_operator_context),
                 db: Session = Depends(get_db)):
    tour_service.delete_photo(db, _tour(db, ctx, tour_id), photo_id)


class PhotoOrder(BaseModel):
    ids: list[int]


@router.put("/tours/{tour_id}/photos/order")
def order_photos(tour_id: int, body: PhotoOrder, ctx: OperatorContext = Depends(get_operator_context),
                 db: Session = Depends(get_db)):
    tour_service.reorder_photos(db, _tour(db, ctx, tour_id), body.ids)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Agenda
# ---------------------------------------------------------------------------
@router.get("/tours/{tour_id}/schedules")
def list_schedules(tour_id: int, ctx: OperatorContext = Depends(get_operator_context), db: Session = Depends(get_db)):
    _tour(db, ctx, tour_id)
    rows = db.scalars(select(TourSchedule).where(TourSchedule.tour_id == tour_id).order_by(TourSchedule.id)).all()
    return [serializers.schedule(s) for s in rows]


@router.post("/tours/{tour_id}/schedules", status_code=201)
def create_schedule(tour_id: int, body: ScheduleIn, ctx: OperatorContext = Depends(get_operator_context),
                    db: Session = Depends(get_db)):
    tour = _tour(db, ctx, tour_id)
    s = TourSchedule(tour_id=tour.id, **body.model_dump())
    db.add(s)
    db.commit()
    schedule_service.generate_for_tour(db, tour)
    return serializers.schedule(s)


def _schedule(db: Session, ctx: OperatorContext, schedule_id: int) -> tuple[TourSchedule, Tour]:
    s = db.get(TourSchedule, schedule_id)
    if not s:
        raise not_found("Regra de agenda")
    return s, _tour(db, ctx, s.tour_id)


@router.put("/schedules/{schedule_id}")
def update_schedule(schedule_id: int, body: ScheduleIn, ctx: OperatorContext = Depends(get_operator_context),
                    db: Session = Depends(get_db)):
    s, tour = _schedule(db, ctx, schedule_id)
    for k, v in body.model_dump().items():
        setattr(s, k, v)
    db.commit()
    schedule_service.generate_for_tour(db, tour)
    return serializers.schedule(s)


@router.delete("/schedules/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: int, ctx: OperatorContext = Depends(get_operator_context),
                    db: Session = Depends(get_db)):
    s, tour = _schedule(db, ctx, schedule_id)
    db.delete(s)
    db.commit()
    schedule_service.generate_for_tour(db, tour)


@router.get("/departures")
def list_departures(
    tour_id: int | None = None,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    ctx: OperatorContext = Depends(get_operator_context),
    db: Session = Depends(get_db),
):
    start = date_from or schedule_service.today_local()
    end = date_to or start + timedelta(days=14)
    stmt = (
        select(Departure).join(Tour, Tour.id == Departure.tour_id)
        .where(Tour.operator_id == ctx.operator.id,
               Departure.starts_at >= datetime.combine(start, datetime.min.time(), tzinfo=TZ),
               Departure.starts_at <= datetime.combine(end, datetime.max.time(), tzinfo=TZ))
        .order_by(Departure.starts_at)
    )
    if tour_id:
        stmt = stmt.where(Departure.tour_id == tour_id)
    deps = db.scalars(stmt.limit(1000)).all()
    titles = {t.id: tour_service_title(t) for t in db.scalars(select(Tour).where(Tour.operator_id == ctx.operator.id)).all()}
    return [{**serializers.departure_operator(d), "title": titles.get(d.tour_id, "")} for d in deps]


@router.post("/tours/{tour_id}/departures", status_code=201)
def create_departure(tour_id: int, body: DepartureIn, ctx: OperatorContext = Depends(get_operator_context),
                     db: Session = Depends(get_db)):
    tour = _tour(db, ctx, tour_id)
    try:
        starts_at = datetime.fromisoformat(body.starts_at_local).replace(tzinfo=TZ)
    except ValueError as exc:
        raise bad_request("invalid_datetime", "Data/hora inválida") from exc
    if starts_at < now_utc():
        raise bad_request("past_datetime", "A saída precisa ser no futuro")
    if db.scalar(select(Departure).where(Departure.tour_id == tour.id, Departure.starts_at == starts_at)):
        raise conflict("duplicate", "Já existe uma saída neste horário")
    dep = Departure(tour_id=tour.id, starts_at=starts_at, capacity=body.capacity, manually_edited=True)
    db.add(dep)
    db.commit()
    return serializers.departure_operator(dep)


@router.patch("/departures/{dep_id}")
def patch_departure(dep_id: int, body: DeparturePatch, ctx: OperatorContext = Depends(get_operator_context),
                    db: Session = Depends(get_db)):
    dep = _departure(db, ctx, dep_id)
    if dep.status == "cancelled":
        raise conflict("cancelled", "Saída cancelada não pode ser editada")
    old = serializers.departure_operator(dep)
    if body.capacity is not None:
        if body.capacity < dep.seats_booked + dep.seats_held:
            raise conflict("capacity_below_booked", "Capacidade menor que as vagas já reservadas")
        dep.capacity = body.capacity
    if body.status is not None:
        dep.status = body.status
    dep.manually_edited = True
    audit(db, ctx.user.id, "departure", dep.id, "update", {"capacity": old["capacity"], "status": old["status"]},
          body.model_dump(exclude_none=True))
    db.commit()
    return serializers.departure_operator(dep)


@router.post("/departures/{dep_id}/cancel")
def cancel_departure(dep_id: int, body: CancelDepartureIn, ctx: OperatorContext = Depends(get_operator_context),
                     db: Session = Depends(get_db)):
    dep = _departure(db, ctx, dep_id)
    n = booking_service.cancel_departure(db, dep, body.reason, ctx.user.id)
    return {"cancelled_bookings": n, "departure": serializers.departure_operator(dep)}


# ---------------------------------------------------------------------------
# Reservas
# ---------------------------------------------------------------------------
@router.get("/bookings")
def list_bookings(
    on_date: date | None = Query(None, alias="date"),
    status: str | None = None,
    tour_id: int | None = None,
    departure_id: int | None = None,
    page: PageParams = Depends(),
    ctx: OperatorContext = Depends(get_operator_context),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Booking).join(Departure, Departure.id == Booking.departure_id)
        .where(Booking.operator_id == ctx.operator.id, Booking.status.not_in(["held", "expired"]))
        .order_by(Departure.starts_at, Booking.id)
    )
    if on_date:
        stmt = stmt.where(
            Departure.starts_at >= datetime.combine(on_date, datetime.min.time(), tzinfo=TZ),
            Departure.starts_at <= datetime.combine(on_date, datetime.max.time(), tzinfo=TZ),
        )
    if status:
        stmt = stmt.where(Booking.status == status)
    if tour_id:
        stmt = stmt.where(Booking.tour_id == tour_id)
    if departure_id:
        stmt = stmt.where(Booking.departure_id == departure_id)
    rows, total = paginate(db, stmt, page)
    return {"items": [serializers.booking(b, db, audience="operator") for b in rows], "total": total,
            "page": page.page, "page_size": page.page_size}


@router.get("/bookings/{code}")
def get_booking(code: str, ctx: OperatorContext = Depends(get_operator_context), db: Session = Depends(get_db)):
    return serializers.booking(_booking(db, ctx, code), db, audience="operator")


@router.post("/bookings/{code}/cancel")
def cancel_booking(code: str, ctx: OperatorContext = Depends(get_operator_context), db: Session = Depends(get_db)):
    b = booking_service.cancel_booking(db, _booking(db, ctx, code), by="operator", reason="operator",
                                       actor_id=ctx.user.id)
    return serializers.booking(b, db, audience="operator")


@router.post("/bookings/{code}/no-show")
def no_show(code: str, ctx: OperatorContext = Depends(get_operator_context), db: Session = Depends(get_db)):
    b = booking_service.mark_no_show(db, _booking(db, ctx, code), ctx.user.id)
    return serializers.booking(b, db, audience="operator")


# ---------------------------------------------------------------------------
# Extrato
# ---------------------------------------------------------------------------
@router.get("/statement")
def statement(
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    ctx: OperatorContext = Depends(get_operator_context),
    db: Session = Depends(get_db),
):
    start = date_from or (schedule_service.today_local() - timedelta(days=30))
    end = date_to or (schedule_service.today_local() + timedelta(days=60))
    rows = db.execute(
        select(Booking, Departure).join(Departure, Departure.id == Booking.departure_id)
        .where(Booking.operator_id == ctx.operator.id,
               Booking.status.in_(["confirmed", "completed", "no_show", "cancelled"]),
               Booking.paid_at.is_not(None),
               Departure.starts_at >= datetime.combine(start, datetime.min.time(), tzinfo=TZ),
               Departure.starts_at <= datetime.combine(end, datetime.max.time(), tzinfo=TZ))
        .order_by(Departure.starts_at.desc())
    ).all()
    items = []
    for b, d in rows:
        earns = b.status in ("confirmed", "completed", "no_show")
        items.append({
            "code": b.code, "title": b.snapshot.get("title"), "starts_at": d.starts_at.isoformat(),
            "status": b.status, "pax_total": b.pax_total, "total_cents": b.total_cents,
            "commission_cents": b.commission_cents if earns else 0,
            "operator_amount_cents": b.operator_amount_cents if earns else 0,
        })
    payouts = db.scalars(select(Payout).where(Payout.operator_id == ctx.operator.id).order_by(Payout.id.desc())).all()
    return {
        "items": items,
        "totals": {
            "gross_cents": sum(i["total_cents"] for i in items if i["status"] != "cancelled"),
            "commission_cents": sum(i["commission_cents"] for i in items),
            "operator_amount_cents": sum(i["operator_amount_cents"] for i in items),
        },
        "pending_payout_cents": payout_service.pending_balance(db, ctx.operator.id),
        "upcoming_amount_cents": payout_service.upcoming_balance(db, ctx.operator.id),
        "payouts": [{"id": p.id, "period_start": p.period_start.isoformat(), "period_end": p.period_end.isoformat(),
                     "amount_cents": p.amount_cents, "status": p.status,
                     "paid_at": p.paid_at.isoformat() if p.paid_at else None} for p in payouts],
    }


@router.get("/members")
def members(ctx: OperatorContext = Depends(get_operator_context), db: Session = Depends(get_db)):
    rows = db.execute(select(OperatorMember, User).join(User, User.id == OperatorMember.user_id)
                      .where(OperatorMember.operator_id == ctx.operator.id)).all()
    return [{"user_id": u.id, "email": u.email, "name": u.name, "role": m.role} for m, u in rows]

