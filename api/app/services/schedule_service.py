"""Agenda: gera saídas (`departures`) a partir das regras de recorrência."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Departure, Tour, TourSchedule

TZ = ZoneInfo("America/Sao_Paulo")
HORIZON_DAYS = 90


def today_local() -> date:
    return datetime.now(TZ).date()


def generate_for_tour(db: Session, tour: Tour, horizon_days: int = HORIZON_DAYS) -> int:
    """Cria as saídas que faltam nos próximos dias. Saídas editadas à mão ou com reservas não são alteradas.
    Saídas futuras sem reservas cujo horário não existe mais em nenhuma regra são removidas."""
    start = today_local()
    end = start + timedelta(days=horizon_days)
    schedules = db.scalars(select(TourSchedule).where(TourSchedule.tour_id == tour.id)).all()
    wanted: dict[datetime, tuple[int, int]] = {}
    for s in schedules:
        d = max(start, s.valid_from)
        last = min(end, s.valid_to) if s.valid_to else end
        while d <= last:
            if d.weekday() in (s.weekdays or []):
                starts_at = datetime.combine(d, s.start_time, tzinfo=TZ)
                wanted[starts_at] = (s.id, s.capacity)
            d += timedelta(days=1)

    created = 0
    for starts_at, (schedule_id, capacity) in wanted.items():
        stmt = (
            insert(Departure)
            .values(
                tour_id=tour.id,
                schedule_id=schedule_id,
                starts_at=starts_at,
                capacity=capacity,
                seats_held=0,
                seats_booked=0,
                status="open",
                manually_edited=False,
            )
            .on_conflict_do_update(
                index_elements=["tour_id", "starts_at"],
                set_={"capacity": capacity, "schedule_id": schedule_id},
                where=(Departure.manually_edited.is_(False))
                & (Departure.seats_booked == 0)
                & (Departure.seats_held == 0)
                & (Departure.status == "open"),
            )
        )
        res = db.execute(stmt)
        created += res.rowcount or 0

    now = datetime.now(TZ)
    db.execute(
        delete(Departure).where(
            Departure.tour_id == tour.id,
            Departure.starts_at > now,
            Departure.schedule_id.is_not(None),
            Departure.manually_edited.is_(False),
            Departure.seats_booked == 0,
            Departure.seats_held == 0,
            Departure.starts_at.not_in(list(wanted.keys())) if wanted else Departure.id.is_not(None),
        )
    )
    db.commit()
    return created


def generate_all(db: Session) -> int:
    tours = db.scalars(select(Tour).where(Tour.status.in_(["published", "pending_review", "draft", "paused"]))).all()
    return sum(generate_for_tour(db, t) for t in tours)
