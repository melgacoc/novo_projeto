"""Reservas do turista, webhooks do gateway e simulador de pagamento (só desenvolvimento)."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import AppError, not_found
from app.core.pagination import PageParams, paginate
from app.core.ratelimit import rate_limit
from app.models import Booking, Payment, User
from app.schemas.booking import BookingCreate, PaymentCreate
from app.services import booking_service, serializers
from app.services.payments import FakeGateway, get_gateway
from app.services.voucher import render_voucher

router = APIRouter(tags=["bookings"])


def _own_booking(db: Session, user: User, code: str) -> Booking:
    b = db.scalar(select(Booking).where(Booking.code == code.upper()))
    if not b or b.user_id != user.id:
        raise not_found("Reserva")
    return b


@router.post("/bookings", status_code=201, dependencies=[Depends(rate_limit("booking-create", 20, 600, per="user"))])
def create_booking(body: BookingCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    b = booking_service.create_hold(
        db, user, departure_id=body.departure_id, quantities=body.quantities, contact_name=body.contact_name,
        contact_phone_e164=body.contact_phone, locale=body.locale if body.locale in ("pt", "es", "en") else "pt",
        source=body.source,
    )
    return serializers.booking(b, db, audience="tourist")


@router.post("/bookings/{code}/payments", dependencies=[Depends(rate_limit("payment-create", 20, 600, per="user"))])
def create_payment(code: str, body: PaymentCreate, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    b = _own_booking(db, user, code)
    p = booking_service.start_payment(db, b, body.method, body.idempotency_key)
    db.refresh(b)
    return {"payment": serializers.payment(p), "booking": serializers.booking(b, db, audience="tourist")}


@router.get("/bookings")
def my_bookings(page: PageParams = Depends(), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Booking).where(Booking.user_id == user.id, Booking.status != "expired").order_by(Booking.id.desc())
    rows, total = paginate(db, stmt, page)
    return {"items": [serializers.booking(b, db, audience="tourist") for b in rows], "total": total,
            "page": page.page, "page_size": page.page_size}


@router.get("/bookings/{code}")
def booking_detail(code: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    b = _own_booking(db, user, code)
    data = serializers.booking(b, db, audience="tourist")
    data["refund_if_cancelled_now_cents"] = (
        booking_service.tourist_refund_amount(b) if b.status == "confirmed" else None
    )
    return data


@router.get("/bookings/{code}/voucher")
def voucher(code: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    b = _own_booking(db, user, code)
    if b.status not in ("confirmed", "completed"):
        raise AppError(409, "not_confirmed", "O voucher fica disponível depois da confirmação")
    pdf = render_voucher(db, b)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="voucher-{b.code}.pdf"'})


@router.post("/bookings/{code}/cancel")
def cancel(code: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    b = _own_booking(db, user, code)
    b = booking_service.cancel_booking(db, b, by="tourist", reason="tourist", actor_id=user.id)
    return serializers.booking(b, db, audience="tourist")


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------
@router.post("/webhooks/payments/{gateway}", tags=["webhooks"], dependencies=[Depends(rate_limit("webhook", 600, 60))])
async def payment_webhook(gateway: str, request: Request, db: Session = Depends(get_db)):
    if gateway != settings.payment_gateway:
        raise not_found("Gateway")
    body = await request.body()
    gw = get_gateway(gateway)
    event = gw.parse_webhook({k.lower(): v for k, v in request.headers.items()}, body)
    booking_service.handle_gateway_event(db, gateway, event)
    return {"received": True}


# ---------------------------------------------------------------------------
# Simulador do gateway "fake" (desenvolvimento)
# ---------------------------------------------------------------------------
@router.post("/dev/payments/{charge_id}/simulate", tags=["dev"])
def simulate_payment(charge_id: str, outcome: str = "approved", user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    if settings.is_production or settings.payment_gateway != "fake":
        raise not_found("Rota")
    payment = db.scalar(select(Payment).where(Payment.gateway_charge_id == charge_id))
    if not payment:
        raise not_found("Pagamento")
    booking = db.get(Booking, payment.booking_id)
    if booking.user_id != user.id and user.role != "admin":
        raise not_found("Pagamento")
    gw = FakeGateway()
    body, headers = gw.build_event(charge_id, "payment.approved" if outcome == "approved" else "payment.failed")
    booking_service.handle_gateway_event(db, "fake", gw.parse_webhook(headers, body))
    db.refresh(booking)
    return serializers.booking(booking, db, audience="tourist")
