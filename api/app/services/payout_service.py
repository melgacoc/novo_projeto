"""Repasses às operadoras (RN11): valor da operadora liberado N dias depois do passeio concluído (ou no-show)."""
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.errors import conflict
from app.core.security import now_utc
from app.models import Booking, Payout, PayoutItem
from app.services import platform_settings


def eligible_bookings(db: Session, operator_id: int | None = None) -> list[Booking]:
    cutoff = now_utc() - timedelta(days=platform_settings.payout_delay_days(db))
    paid_ids = select(PayoutItem.booking_id)
    stmt = select(Booking).where(
        (
            ((Booking.status == "completed") & (Booking.completed_at <= cutoff))
            | ((Booking.status == "no_show") & (Booking.no_show_at <= cutoff))
        ),
        Booking.id.not_in(paid_ids),
    )
    if operator_id:
        stmt = stmt.where(Booking.operator_id == operator_id)
    return list(db.scalars(stmt).all())


def generate(db: Session, actor_id: int | None) -> list[Payout]:
    groups: dict[int, list[Booking]] = defaultdict(list)
    for b in eligible_bookings(db):
        groups[b.operator_id].append(b)
    payouts = []
    today = date.today()
    for operator_id, bookings in groups.items():
        dates = [date.fromisoformat(b.snapshot["starts_at"][:10]) for b in bookings]
        payout = Payout(
            operator_id=operator_id,
            period_start=min(dates),
            period_end=max(dates) if dates else today,
            amount_cents=sum(b.operator_amount_cents for b in bookings),
            status="pending",
        )
        for b in bookings:
            payout.items.append(PayoutItem(booking_id=b.id, amount_cents=b.operator_amount_cents))
        db.add(payout)
        payouts.append(payout)
    db.flush()
    for p in payouts:
        audit(db, actor_id, "payout", p.id, "generate", None, {"operator_id": p.operator_id, "amount": p.amount_cents})
    db.commit()
    return payouts


def mark_paid(db: Session, payout: Payout, actor_id: int | None, transfer_id: str | None, notes: str) -> Payout:
    if payout.status == "paid":
        raise conflict("already_paid", "Repasse já marcado como pago")
    payout.status = "paid"
    payout.paid_at = now_utc()
    payout.gateway_transfer_id = transfer_id
    payout.notes = notes
    audit(db, actor_id, "payout", payout.id, "mark_paid", None, {"transfer_id": transfer_id})
    db.commit()
    return payout


def pending_balance(db: Session, operator_id: int) -> int:
    return sum(b.operator_amount_cents for b in eligible_bookings(db, operator_id))


def upcoming_balance(db: Session, operator_id: int) -> int:
    """Reservas confirmadas ainda não realizadas (a receber depois do passeio)."""
    return int(
        db.scalar(
            select(func.coalesce(func.sum(Booking.operator_amount_cents), 0)).where(
                Booking.operator_id == operator_id, Booking.status == "confirmed"
            )
        )
        or 0
    )
