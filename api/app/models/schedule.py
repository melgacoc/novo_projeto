from datetime import date, datetime, time

from sqlalchemy import ARRAY, BigInteger, Date, DateTime, ForeignKey, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin

DEPARTURE_STATUSES = ("open", "closed", "cancelled")


class TourSchedule(TimestampMixin, Base):
    """Regra de recorrência: gera `departures` para os próximos dias."""

    __tablename__ = "tour_schedules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id", ondelete="CASCADE"), index=True)
    weekdays: Mapped[list[int]] = mapped_column(ARRAY(Integer))  # 0 = segunda ... 6 = domingo
    start_time: Mapped[time] = mapped_column(Time)
    capacity: Mapped[int] = mapped_column(Integer)
    valid_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)


class Departure(TimestampMixin, Base):
    """Saída concreta. Vagas livres = capacity - seats_held - seats_booked."""

    __tablename__ = "departures"
    __table_args__ = (UniqueConstraint("tour_id", "starts_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id", ondelete="CASCADE"), index=True)
    schedule_id: Mapped[int | None] = mapped_column(ForeignKey("tour_schedules.id", ondelete="SET NULL"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    capacity: Mapped[int] = mapped_column(Integer)
    seats_held: Mapped[int] = mapped_column(Integer, default=0)
    seats_booked: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(20))
    # editada manualmente pela operadora: a geração automática não sobrescreve
    manually_edited: Mapped[bool] = mapped_column(default=False)

    @property
    def seats_available(self) -> int:
        return max(0, self.capacity - self.seats_held - self.seats_booked)
