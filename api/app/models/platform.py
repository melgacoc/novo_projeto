from sqlalchemy import JSON, BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin

DEFAULT_SETTINGS: dict[str, str] = {
    "default_commission_rate": "0.10",
    "hold_minutes": "15",
    "payout_delay_days": "2",
    "low_availability_min_seats": "3",
}


class PlatformSetting(TimestampMixin, Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[str] = mapped_column(String(255))


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    entity: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[str] = mapped_column(String(40), index=True)
    action: Mapped[str] = mapped_column(String(40))
    old_values: Mapped[dict | None] = mapped_column(JSON)
    new_values: Mapped[dict | None] = mapped_column(JSON)
