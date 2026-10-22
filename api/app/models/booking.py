from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

BOOKING_STATUSES = ("held", "awaiting_operator", "confirmed", "expired", "cancelled", "no_show", "completed")


class Booking(TimestampMixin, Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    departure_id: Mapped[int] = mapped_column(ForeignKey("departures.id"), index=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"), index=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey("operators.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="held", index=True)
    locale: Mapped[str] = mapped_column(String(5), default="pt")
    contact_name: Mapped[str] = mapped_column(String(160))
    contact_phone_e164: Mapped[str] = mapped_column(String(20))
    contact_email: Mapped[str] = mapped_column(String(255))
    pax_total: Mapped[int] = mapped_column(Integer)
    # valores congelados no momento da reserva
    subtotal_cents: Mapped[int] = mapped_column(Integer)
    service_fee_cents: Mapped[int] = mapped_column(Integer, default=0)
    total_cents: Mapped[int] = mapped_column(Integer)
    commission_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    commission_cents: Mapped[int] = mapped_column(Integer)
    operator_amount_cents: Mapped[int] = mapped_column(Integer)
    hold_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by: Mapped[str | None] = mapped_column(String(20))
    cancel_reason: Mapped[str | None] = mapped_column(String(40))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    no_show_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refund_amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str | None] = mapped_column(String(120))
    # snapshot do passeio na hora da reserva (título no idioma, data/hora da saída)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)

    items: Mapped[list["BookingItem"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class BookingItem(TimestampMixin, Base):
    __tablename__ = "booking_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), index=True)
    price_category_code: Mapped[str] = mapped_column(String(20))
    label: Mapped[str] = mapped_column(String(60), default="")
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_cents: Mapped[int] = mapped_column(Integer)


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), index=True)
    gateway: Mapped[str] = mapped_column(String(30))
    gateway_charge_id: Mapped[str] = mapped_column(String(120), unique=True)
    method: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    fee_cents: Mapped[int] = mapped_column(Integer, default=0)
    pix_qr_code: Mapped[str | None] = mapped_column(Text)
    pix_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checkout_url: Mapped[str | None] = mapped_column(String(500))
    idempotency_key: Mapped[str | None] = mapped_column(String(80), unique=True)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)


class Refund(TimestampMixin, Base):
    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), index=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(60))
    gateway_refund_id: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="pending")


class Payout(TimestampMixin, Base):
    __tablename__ = "payouts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey("operators.id"), index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    amount_cents: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    gateway_transfer_id: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str] = mapped_column(Text, default="")

    items: Mapped[list["PayoutItem"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class PayoutItem(TimestampMixin, Base):
    __tablename__ = "payout_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    payout_id: Mapped[int] = mapped_column(ForeignKey("payouts.id", ondelete="CASCADE"), index=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), unique=True)
    amount_cents: Mapped[int] = mapped_column(Integer)


class WebhookEvent(TimestampMixin, Base):
    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    gateway: Mapped[str] = mapped_column(String(30))
    event_id: Mapped[str] = mapped_column(String(120), unique=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
