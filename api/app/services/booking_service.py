"""Ciclo de vida da reserva (spec §5): retenção, pagamento, confirmação, cancelamentos, no-show, conclusão."""
import logging
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.config import settings
from app.core.errors import AppError, bad_request, conflict, not_found
from app.core.security import new_booking_code, now_utc
from app.models import (
    Booking,
    BookingItem,
    Departure,
    Operator,
    Payment,
    Refund,
    Tour,
    User,
    WebhookEvent,
)
from app.services import email_service, platform_settings, pricing
from app.services.catalog_service import tour_text
from app.services.payments import GatewayEvent, get_gateway
from app.services.schedule_service import TZ

log = logging.getLogger("app.bookings")


def fmt_money(cents: int) -> str:
    return f"R$ {cents / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_when(starts_at: datetime) -> str:
    return starts_at.astimezone(TZ).strftime("%d/%m/%Y %H:%M")


def commission_rate_for(db: Session, operator: Operator) -> Decimal:
    if operator.commission_rate is not None:
        return Decimal(operator.commission_rate)
    return platform_settings.default_commission_rate(db)


def is_bookable(tour: Tour, dep: Departure, at: datetime | None = None) -> bool:
    at = at or now_utc()
    return (
        tour.status == "published"
        and dep.status == "open"
        and dep.starts_at - timedelta(minutes=tour.booking_cutoff_minutes) > at
    )


# ---------------------------------------------------------------------------
# Retenção da vaga
# ---------------------------------------------------------------------------
def create_hold(
    db: Session,
    user: User,
    *,
    departure_id: int,
    quantities: dict[str, int],
    contact_name: str,
    contact_phone_e164: str,
    locale: str,
    source: str | None = None,
) -> Booking:
    dep = db.get(Departure, departure_id)
    if not dep:
        raise not_found("Saída")
    tour = db.get(Tour, dep.tour_id)
    operator = db.get(Operator, tour.operator_id)
    if operator.status != "active" or not is_bookable(tour, dep):
        raise conflict("not_bookable", "Esta saída não está disponível para reserva")

    q = pricing.quote(tour, dep.starts_at.astimezone(TZ).date(), quantities, locale)

    # retenção atômica: só reserva se houver vaga (spec §5.1)
    res = db.execute(
        update(Departure)
        .where(
            Departure.id == dep.id,
            Departure.status == "open",
            Departure.capacity - Departure.seats_held - Departure.seats_booked >= q.pax_total,
        )
        .values(seats_held=Departure.seats_held + q.pax_total)
    )
    if res.rowcount != 1:
        db.rollback()
        raise conflict("no_availability", "Não há vagas suficientes nesta saída")

    rate = commission_rate_for(db, operator)
    commission = int((Decimal(q.subtotal_cents) * rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    booking = Booking(
        code=new_booking_code(),
        user_id=user.id,
        departure_id=dep.id,
        tour_id=tour.id,
        operator_id=operator.id,
        status="held",
        locale=locale,
        contact_name=contact_name.strip(),
        contact_phone_e164=contact_phone_e164,
        contact_email=user.email,
        pax_total=q.pax_total,
        subtotal_cents=q.subtotal_cents,
        service_fee_cents=0,
        total_cents=q.subtotal_cents,
        commission_rate=rate,
        commission_cents=commission,
        operator_amount_cents=q.subtotal_cents - commission,
        hold_expires_at=now_utc() + timedelta(minutes=platform_settings.hold_minutes(db)),
        source=(source or None),
        snapshot={
            "title": tour_text(tour, locale).title,
            "tour_slug": tour.slug,
            "starts_at": dep.starts_at.isoformat(),
            "duration_minutes": tour.duration_minutes,
            "area": tour.public_area_label,
            "operator_name": operator.public_name,
            "cancellation_policy": tour.cancellation_policy,
            "on_site_fees_note": tour.on_site_fees_note,
        },
    )
    for line in q.lines:
        booking.items.append(
            BookingItem(
                price_category_code=line.code,
                label=line.label,
                quantity=line.quantity,
                unit_price_cents=line.unit_price_cents,
            )
        )
    # perfil: guarda nome/telefone na primeira reserva
    if not user.name:
        user.name = contact_name.strip()
    if not user.phone_e164:
        user.phone_e164 = contact_phone_e164
    db.add(booking)
    db.commit()
    return booking


def expire_holds(db: Session) -> int:
    rows = db.scalars(
        select(Booking)
        .where(Booking.status == "held", Booking.hold_expires_at < now_utc())
        .with_for_update(skip_locked=True)
    ).all()
    for b in rows:
        db.execute(
            update(Departure)
            .where(Departure.id == b.departure_id)
            .values(seats_held=Departure.seats_held - b.pax_total)
        )
        b.status = "expired"
    db.commit()
    return len(rows)


# ---------------------------------------------------------------------------
# Pagamento
# ---------------------------------------------------------------------------
def start_payment(db: Session, booking: Booking, method: str, idempotency_key: str | None) -> Payment:
    if method not in ("pix", "card"):
        raise bad_request("invalid_method", "Forma de pagamento inválida")
    if idempotency_key:
        existing = db.scalar(select(Payment).where(Payment.idempotency_key == idempotency_key))
        if existing:
            if existing.booking_id != booking.id:
                raise conflict("idempotency_conflict", "Chave de idempotência já usada")
            return existing
    if booking.status != "held" or (booking.hold_expires_at and booking.hold_expires_at < now_utc()):
        raise conflict("hold_expired", "O tempo para pagar acabou. Faça a reserva novamente.")
    pending = db.scalar(
        select(Payment).where(
            Payment.booking_id == booking.id, Payment.method == method, Payment.status == "pending"
        )
    )
    if pending:
        return pending
    gateway = get_gateway()
    result = gateway.create_charge(
        reference=booking.code,
        method=method,
        amount_cents=booking.total_cents,
        expires_at=booking.hold_expires_at,
        customer={"name": booking.contact_name, "email": booking.contact_email, "phone": booking.contact_phone_e164},
        description=booking.snapshot.get("title", "Passeio"),
        idempotency_key=idempotency_key or f"{booking.code}-{method}",
    )
    payment = Payment(
        booking_id=booking.id,
        gateway=gateway.name,
        gateway_charge_id=result.charge_id,
        method=method,
        status=result.status,
        amount_cents=booking.total_cents,
        fee_cents=result.fee_cents,
        pix_qr_code=result.pix_qr_code,
        pix_expires_at=result.pix_expires_at,
        checkout_url=result.checkout_url,
        idempotency_key=idempotency_key,
        raw=result.raw,
    )
    db.add(payment)
    db.commit()
    if result.status == "approved":
        on_payment_approved(db, payment)
    return payment


def handle_gateway_event(db: Session, gateway_name: str, event: GatewayEvent) -> None:
    """Processa um evento do gateway de forma idempotente (por event_id)."""
    if db.scalar(select(WebhookEvent).where(WebhookEvent.event_id == event.event_id)):
        return
    row = WebhookEvent(
        gateway=gateway_name,
        event_id=event.event_id,
        payload={"type": event.type, "charge_id": event.charge_id, "raw": event.raw},
    )
    db.add(row)
    db.commit()
    _process_event(db, event)


def reprocess_failed_webhooks(db: Session, max_age_hours: int = 48) -> int:
    """Tenta de novo os webhooks que falharam (ex.: pagamento chegou antes da reserva ser gravada)."""
    rows = db.scalars(
        select(WebhookEvent).where(
            WebhookEvent.processed_at.is_(None),
            WebhookEvent.error.is_not(None),
            WebhookEvent.created_at > now_utc() - timedelta(hours=max_age_hours),
        )
    ).all()
    for row in rows:
        p = row.payload or {}
        if "type" in p and "charge_id" in p:
            _process_event(db, GatewayEvent(event_id=row.event_id, type=p["type"], charge_id=p["charge_id"], raw=p.get("raw", {})))
    return len(rows)


def _process_event(db: Session, event: GatewayEvent) -> None:
    try:
        payment = db.scalar(select(Payment).where(Payment.gateway_charge_id == event.charge_id))
        if not payment:
            raise ValueError(f"pagamento não encontrado: {event.charge_id}")
        if event.type == "payment.approved":
            on_payment_approved(db, payment)
        elif event.type == "payment.failed":
            if payment.status == "pending":
                payment.status = "failed"
        elif event.type == "chargeback":
            payment.status = "chargeback"
            audit(db, None, "payment", payment.id, "chargeback")
        row = db.scalar(select(WebhookEvent).where(WebhookEvent.event_id == event.event_id))
        row.processed_at = now_utc()
        row.error = None
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        row = db.scalar(select(WebhookEvent).where(WebhookEvent.event_id == event.event_id))
        row.error = str(exc)[:1000]
        db.commit()
        log.exception("falha ao processar webhook %s", event.event_id)


def on_payment_approved(db: Session, payment: Payment) -> None:
    if payment.status == "approved":
        return
    payment.status = "approved"
    booking = db.scalar(select(Booking).where(Booking.id == payment.booking_id).with_for_update())
    booking.paid_at = now_utc()
    dep = db.get(Departure, booking.departure_id)

    if booking.status == "held":
        db.execute(
            update(Departure)
            .where(Departure.id == dep.id)
            .values(
                seats_held=Departure.seats_held - booking.pax_total,
                seats_booked=Departure.seats_booked + booking.pax_total,
            )
        )
        _confirm(db, booking)
        return

    if booking.status == "expired":
        # pagamento chegou depois da retenção expirar (comum com Pix): confirma se ainda houver vaga
        res = db.execute(
            update(Departure)
            .where(
                Departure.id == dep.id,
                Departure.status == "open",
                Departure.capacity - Departure.seats_held - Departure.seats_booked >= booking.pax_total,
            )
            .values(seats_booked=Departure.seats_booked + booking.pax_total)
        )
        if res.rowcount == 1:
            _confirm(db, booking)
        else:
            booking.status = "cancelled"
            booking.cancelled_at = now_utc()
            booking.cancelled_by = "system"
            booking.cancel_reason = "no_availability"
            db.commit()
            _refund(db, booking, booking.total_cents, "no_availability")
            _notify_cancelled(db, booking)
        return

    # já confirmada/cancelada: nada a fazer além de registrar o pagamento
    db.commit()


def _confirm(db: Session, booking: Booking) -> None:
    booking.status = "confirmed"
    booking.confirmed_at = now_utc()
    booking.hold_expires_at = None
    db.commit()
    title = booking.snapshot.get("title", "")
    when = fmt_when(datetime.fromisoformat(booking.snapshot["starts_at"]))
    link = f"{settings.primary_frontend_url}/{booking.locale}/reservas/{booking.code}"
    subject, html = email_service.render(
        "booking_confirmed", booking.locale, title=title, code=booking.code, when=when, link=link
    )
    email_service.enqueue_email(booking.contact_email, subject, html, attach_voucher_booking_id=booking.id)
    operator = db.get(Operator, booking.operator_id)
    if operator.contact_email:
        email_service.enqueue_email(
            operator.contact_email,
            f"Nova reserva {booking.code}: {title}",
            f"<p>Nova reserva <b>{booking.code}</b> para <b>{title}</b> em {when}: "
            f"{booking.pax_total} pessoa(s), {booking.contact_name}. Valor para a operadora: "
            f"{fmt_money(booking.operator_amount_cents)}.</p>",
        )


# ---------------------------------------------------------------------------
# Reembolso e cancelamentos
# ---------------------------------------------------------------------------
def _refund(db: Session, booking: Booking, amount_cents: int, reason: str) -> int:
    if amount_cents <= 0:
        return 0
    payment = db.scalar(
        select(Payment).where(
            Payment.booking_id == booking.id, Payment.status.in_(["approved", "partially_refunded"])
        )
    )
    if not payment:
        return 0
    amount_cents = min(amount_cents, payment.amount_cents - booking.refund_amount_cents)
    if amount_cents <= 0:
        return 0
    gateway = get_gateway(payment.gateway)
    refund_id = gateway.refund(charge_id=payment.gateway_charge_id, amount_cents=amount_cents)
    db.add(
        Refund(
            payment_id=payment.id,
            booking_id=booking.id,
            amount_cents=amount_cents,
            reason=reason,
            gateway_refund_id=refund_id,
            status="completed",
        )
    )
    booking.refund_amount_cents += amount_cents
    payment.status = "refunded" if booking.refund_amount_cents >= payment.amount_cents else "partially_refunded"
    db.commit()
    return amount_cents


def tourist_refund_amount(booking: Booking, at: datetime | None = None) -> int:
    """RN06: flexible = integral até 24 h antes; moderate = até 48 h; strict = sem reembolso."""
    at = at or now_utc()
    starts_at = datetime.fromisoformat(booking.snapshot["starts_at"])
    hours = (starts_at - at).total_seconds() / 3600
    policy = booking.snapshot.get("cancellation_policy", "flexible")
    limit = {"flexible": 24, "moderate": 48}.get(policy)
    if limit is not None and hours >= limit:
        return booking.total_cents
    return 0


def cancel_booking(
    db: Session,
    booking: Booking,
    *,
    by: str,
    reason: str,
    actor_id: int | None,
    refund_cents: int | None = None,
) -> Booking:
    booking = db.scalar(select(Booking).where(Booking.id == booking.id).with_for_update())
    if booking.status == "held":
        db.execute(
            update(Departure)
            .where(Departure.id == booking.departure_id)
            .values(seats_held=Departure.seats_held - booking.pax_total)
        )
        booking.status = "cancelled"
        booking.cancelled_at = now_utc()
        booking.cancelled_by = by
        booking.cancel_reason = reason
        db.commit()
        return booking
    if booking.status != "confirmed":
        raise conflict("not_cancellable", "Esta reserva não pode ser cancelada")

    if refund_cents is None:
        refund_cents = tourist_refund_amount(booking) if by == "tourist" else booking.total_cents
    db.execute(
        update(Departure)
        .where(Departure.id == booking.departure_id)
        .values(seats_booked=Departure.seats_booked - booking.pax_total)
    )
    booking.status = "cancelled"
    booking.cancelled_at = now_utc()
    booking.cancelled_by = by
    booking.cancel_reason = reason
    if by == "operator":
        op = db.get(Operator, booking.operator_id)
        op.cancellations_count += 1
    audit(db, actor_id, "booking", booking.code, "cancel", None, {"by": by, "reason": reason, "refund": refund_cents})
    db.commit()
    _refund(db, booking, refund_cents, reason)
    _notify_cancelled(db, booking)
    return booking


def _notify_cancelled(db: Session, booking: Booking) -> None:
    title = booking.snapshot.get("title", "")
    when = fmt_when(datetime.fromisoformat(booking.snapshot["starts_at"]))
    reason_key = booking.cancel_reason if booking.cancel_reason in email_service.REASONS else booking.cancelled_by
    subject, html = email_service.render(
        "booking_cancelled",
        booking.locale,
        title=title,
        code=booking.code,
        when=when,
        reason=email_service.reason_text(reason_key, booking.locale),
        refund=fmt_money(booking.refund_amount_cents),
    )
    email_service.enqueue_email(booking.contact_email, subject, html)


def cancel_departure(db: Session, departure: Departure, reason: str, actor_id: int | None) -> int:
    """RN07: cancela a saída e todas as reservas dela com reembolso integral."""
    if departure.status == "cancelled":
        return 0
    departure.status = "cancelled"
    departure.cancel_reason = reason
    departure.manually_edited = True
    audit(db, actor_id, "departure", departure.id, "cancel", None, {"reason": reason})
    db.commit()
    bookings = db.scalars(
        select(Booking).where(Booking.departure_id == departure.id, Booking.status.in_(["held", "confirmed"]))
    ).all()
    for b in bookings:
        by = "operator" if reason == "operator" else "system"
        cancel_booking(db, b, by=by, reason=reason, actor_id=actor_id, refund_cents=b.total_cents)
    return len(bookings)


def mark_no_show(db: Session, booking: Booking, actor_id: int | None) -> Booking:
    """RN15: a operadora marca no-show entre o início da saída e 24 h depois. Sem reembolso."""
    if booking.status != "confirmed":
        raise conflict("invalid_status", "Só reservas confirmadas podem ser marcadas como no-show")
    starts_at = datetime.fromisoformat(booking.snapshot["starts_at"])
    now = now_utc()
    if now < starts_at or now > starts_at + timedelta(hours=24):
        raise conflict("no_show_window", "No-show só pode ser marcado até 24 h depois do início da saída")
    booking.status = "no_show"
    booking.no_show_at = now
    audit(db, actor_id, "booking", booking.code, "no_show")
    db.commit()
    return booking


def complete_finished(db: Session) -> int:
    rows = db.execute(
        select(Booking, Departure, Tour)
        .join(Departure, Departure.id == Booking.departure_id)
        .join(Tour, Tour.id == Booking.tour_id)
        .where(Booking.status == "confirmed", Departure.starts_at < now_utc())
    ).all()
    n = 0
    for booking, dep, tour in rows:
        if dep.starts_at + timedelta(minutes=tour.duration_minutes) < now_utc():
            booking.status = "completed"
            booking.completed_at = now_utc()
            n += 1
    db.commit()
    return n
