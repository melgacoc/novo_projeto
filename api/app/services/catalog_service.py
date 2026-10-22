"""Catálogo público: textos por idioma, busca com filtros e proximidade, disponibilidade (RN09, RN10)."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import Date, and_, cast, exists, func, or_, select
from sqlalchemy.orm import Session

from app.core.security import now_utc
from app.models import Category, Departure, Operator, Tour, TourTranslation
from app.models.catalog import LOCALES
from app.services.schedule_service import TZ

PUBLIC_PRECISION = 2  # ~1 km: o mapa público mostra só a região aproximada


@dataclass
class TourText:
    title: str
    summary: str
    description: str
    includes: str
    excludes: str
    what_to_bring: str
    meeting_point_details: str


def tour_text(tour: Tour, locale: str) -> TourText:
    by = {t.locale: t for t in tour.translations}
    for loc in (locale, "pt", "es", "en"):
        t = by.get(loc)
        if t and t.title:
            return TourText(t.title, t.summary, t.description, t.includes, t.excludes, t.what_to_bring,
                            t.meeting_point_details)
    return TourText("", "", "", "", "", "", "")


def set_locations(tour: Tour, lat: float | None, lng: float | None) -> None:
    """Grava o ponto de encontro exato (privado) e deriva a região pública arredondada."""
    if lat is None or lng is None:
        tour.meeting_lat = tour.meeting_lng = tour.public_lat = tour.public_lng = None
        tour.meeting_point_location = tour.public_location = None
        return
    tour.meeting_lat, tour.meeting_lng = lat, lng
    tour.meeting_point_location = f"SRID=4326;POINT({lng} {lat})"
    plat, plng = round(lat, PUBLIC_PRECISION), round(lng, PUBLIC_PRECISION)
    tour.public_lat, tour.public_lng = plat, plng
    tour.public_location = f"SRID=4326;POINT({plng} {plat})"


def availability_label(dep: Departure, min_seats: int) -> str:
    free = dep.seats_available
    if free <= 0:
        return "sold_out"
    if free <= max(min_seats, int(dep.capacity * 0.2)):
        return "last_seats"
    return "available"


def _local_ts(col):
    return func.timezone("America/Sao_Paulo", col)


@dataclass
class SearchFilters:
    q: str | None = None
    category: str | None = None
    price_min: int | None = None
    price_max: int | None = None
    on_date: date | None = None
    time_from: time | None = None
    time_to: time | None = None
    available: bool = False
    pax: int = 1
    lat: float | None = None
    lng: float | None = None
    radius_km: float | None = None
    sort: str = "relevance"
    locale: str = "pt"


def search(db: Session, f: SearchFilters, offset: int, limit: int) -> tuple[list[tuple[Tour, float | None]], int]:
    point = None
    distance = None
    if f.lat is not None and f.lng is not None:
        point = func.ST_GeogFromText(f"SRID=4326;POINT({float(f.lng)} {float(f.lat)})")
        distance = func.ST_Distance(Tour.public_location, point)

    cols = [Tour] + ([distance.label("distance")] if distance is not None else [])
    stmt = (
        select(*cols)
        .join(Operator, Operator.id == Tour.operator_id)
        .where(Tour.status == "published", Operator.status == "active")
    )
    if f.category:
        stmt = stmt.join(Category, Category.id == Tour.category_id).where(Category.slug == f.category)
    if f.q:
        like = f"%{f.q.strip()}%"
        stmt = stmt.where(
            exists().where(
                TourTranslation.tour_id == Tour.id,
                or_(TourTranslation.title.ilike(like), TourTranslation.summary.ilike(like)),
            )
            | Tour.public_area_label.ilike(like)
        )
    if f.price_min is not None:
        stmt = stmt.where(Tour.from_price_cents >= f.price_min)
    if f.price_max is not None:
        stmt = stmt.where(Tour.from_price_cents <= f.price_max)

    if f.available or f.on_date or f.time_from or f.time_to:
        local = _local_ts(Departure.starts_at)
        conds = [
            Departure.tour_id == Tour.id,
            Departure.status == "open",
            Departure.starts_at - func.make_interval(0, 0, 0, 0, 0, Tour.booking_cutoff_minutes) > now_utc(),
            Departure.capacity - Departure.seats_held - Departure.seats_booked >= max(f.pax, 1),
        ]
        if f.on_date:
            conds.append(cast(local, Date) == f.on_date)
        else:
            # sem data: considera os próximos 30 dias
            conds.append(Departure.starts_at < now_utc() + timedelta(days=30))
        if f.time_from:
            conds.append(func.to_char(local, "HH24:MI") >= f.time_from.strftime("%H:%M"))
        if f.time_to:
            conds.append(func.to_char(local, "HH24:MI") <= f.time_to.strftime("%H:%M"))
        stmt = stmt.where(exists().where(and_(*conds)))

    if point is not None and f.radius_km:
        stmt = stmt.where(func.ST_DWithin(Tour.public_location, point, float(f.radius_km) * 1000))

    if f.sort == "price":
        stmt = stmt.order_by(Tour.from_price_cents.asc().nulls_last(), Tour.id)
    elif f.sort == "distance" and distance is not None:
        stmt = stmt.order_by(distance.asc().nulls_last(), Tour.id)
    else:
        # relevância: penaliza operadoras com cancelamentos (RN08), depois avaliação e novidade
        stmt = stmt.order_by(
            Operator.cancellations_count.asc(), Tour.rating_avg.desc().nulls_last(), Tour.id.desc()
        )

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.execute(stmt.offset(offset).limit(limit)).all()
    out = []
    for row in rows:
        tour = row[0]
        dist = float(row[1]) if distance is not None and row[1] is not None else None
        out.append((tour, dist))
    return out, total


def next_departures(db: Session, tour_ids: list[int]) -> dict[int, datetime]:
    if not tour_ids:
        return {}
    rows = db.execute(
        select(Departure.tour_id, func.min(Departure.starts_at))
        .join(Tour, Tour.id == Departure.tour_id)
        .where(
            Departure.tour_id.in_(tour_ids),
            Departure.status == "open",
            Departure.starts_at - func.make_interval(0, 0, 0, 0, 0, Tour.booking_cutoff_minutes) > now_utc(),
            Departure.capacity - Departure.seats_held - Departure.seats_booked > 0,
        )
        .group_by(Departure.tour_id)
    ).all()
    return {tid: ts for tid, ts in rows}


def public_departures(db: Session, tour: Tour, start: date, end: date) -> list[Departure]:
    start_dt = datetime.combine(start, time.min, tzinfo=TZ)
    end_dt = datetime.combine(end, time.max, tzinfo=TZ)
    cutoff = now_utc() + timedelta(minutes=tour.booking_cutoff_minutes)
    return list(
        db.scalars(
            select(Departure)
            .where(
                Departure.tour_id == tour.id,
                Departure.status == "open",
                Departure.starts_at >= max(start_dt, cutoff),
                Departure.starts_at <= end_dt,
            )
            .order_by(Departure.starts_at)
        ).all()
    )


def category_name(cat: Category | None, locale: str) -> str:
    if not cat:
        return ""
    return getattr(cat, f"name_{locale}", None) or cat.name_pt


def valid_locale(locale: str | None) -> str:
    return locale if locale in LOCALES else "pt"
