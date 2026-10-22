from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

OPERATOR_STATUSES = ("invited", "pending_review", "active", "suspended")


class Operator(TimestampMixin, Base):
    __tablename__ = "operators"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # nome exibido ao turista (aprovado pelo admin); dados de contato nunca são públicos
    public_name: Mapped[str] = mapped_column(String(120))
    trade_name: Mapped[str] = mapped_column(String(160))
    legal_name: Mapped[str] = mapped_column(String(200), default="")
    document: Mapped[str] = mapped_column(String(20), default="")
    cadastur_number: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(20), default="pending_review")
    # nulo = usa a comissão padrão da plataforma (settings.default_commission_rate)
    commission_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    contact_phone: Mapped[str] = mapped_column(String(20), default="")
    contact_email: Mapped[str] = mapped_column(String(255), default="")
    gateway_recipient_id: Mapped[str | None] = mapped_column(String(120))
    cancellations_count: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")

    members: Mapped[list["OperatorMember"]] = relationship(back_populates="operator", cascade="all, delete-orphan")


class OperatorMember(TimestampMixin, Base):
    __tablename__ = "operator_members"
    __table_args__ = (UniqueConstraint("operator_id", "user_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey("operators.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="owner")

    operator: Mapped[Operator] = relationship(back_populates="members")


class OperatorInvite(TimestampMixin, Base):
    __tablename__ = "operator_invites"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey("operators.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(255))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
