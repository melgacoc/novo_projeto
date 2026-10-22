"""Rotas públicas (sem login): configuração, catálogo, saídas, cotação e geocodificação."""
from datetime import date, time, timedelta

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import not_found
from app.core.pagination import PageParams
from app.core.ratelimit import rate_limit
from app.models import Category, Departure, Operator, Tour
from app.schemas.booking import QuoteIn
from app.services import catalog_service, geocoding, platform_settings, pricing, serializers
from app.services.catalog_service import SearchFilters, valid_locale
from app.services.schedule_service import TZ, today_local

router = APIRouter(tags=["public"])


def locale_param(request: Request, locale: str | None = Query(None)) -> str:
    if locale:
        return valid_locale(locale)
    header = (request.headers.get("accept-language") or "pt")[:2].lower()
    return valid_locale(header)


@router.get("/config")
def config(db: Session = Depends(get_db)):
    return {
        "app_name": settings.app_name,
        "env": settings.app_env,
        "auth_enabled": settings.auth_enabled,
        "google_login": settings.google_configured,
        "payment_gateway": settings.payment_gateway,
        "locales": ["pt", "es", "en"],
        "hold_minutes": platform_settings.hold_minutes(db),
        "map": {"style_url": "https://tiles.openfreemap.org/styles/liberty", "center": [-43.1729, -22.9068]},
    }


@router.get("/categories")
def categories(locale: str = Depends(locale_param), db: Session = Depends(get_db)):
    cats = db.scalars(select(Category).order_by(Category.position, Category.id)).all()
    return [serializers.category(c, locale) for c in cats]


def _cats(db: Session) -> dict[int, Category]:
    return {c.id: c for c in db.scalars(select(Category)).all()}


@router.get("/tours", dependencies=[Depends(rate_limit("search", 120, 60))])
def search_tours(
    locale: str = Depends(locale_param),
    page: PageParams = Depends(),
    q: str | None = Query(None, max_length=100),
    category: str | None = None,
    price_min: int | None = Query(None, ge=0),
    price_max: int | None = Query(None, ge=0),
    on_date: date | None = Query(None, alias="date"),
    time_from: time | None = None,
    time_to: time | None = None,
    available: bool = False,
    pax: int = Query(1, ge=1, le=50),
    lat: float | None = Query(None, ge=-90, le=90),
    lng: float | None = Query(None, ge=-180, le=180),
    radius_km: float | None = Query(None, gt=0, le=300),
    sort: str = Query("relevance", pattern="^(relevance|price|distance)$"),
    db: Session = Depends(get_db),
):
    f = SearchFilters(q=q, category=category, price_min=price_min, price_max=price_max, on_date=on_date,
                      time_from=time_from, time_to=time_to, available=available, pax=pax, lat=lat, lng=lng,
                      radius_km=radius_km, sort=sort, locale=locale)
    rows, total = catalog_service.search(db, f, page.offset, page.page_size)
    cats = _cats(db)
    ops = {o.id: o for o in db.scalars(select(Operator).where(Operator.id.in_({t.operator_id for t, _ in rows}))).all()}
    nexts = catalog_service.next_departures(db, [t.id for t, _ in rows])
    items = [serializers.tour_card(t, locale, cats, ops.get(t.operator_id), nexts.get(t.id), d) for t, d in rows]
    return {"items": items, "total": total, "page": page.page, "page_size": page.page_size}


def _published(db: Session, slug: str) -> Tour:
    tour = db.scalar(select(Tour).where(Tour.slug == slug))
    if not tour or tour.status != "published":
        raise not_found("Passeio")
    op = db.get(Operator, tour.operator_id)
    if op.status != "active":
        raise not_found("Passeio")
    return tour


@router.get("/tours/{slug}")
def tour_detail(slug: str, locale: str = Depends(locale_param), db: Session = Depends(get_db)):
    tour = _published(db, slug)
    op = db.get(Operator, tour.operator_id)
    data = serializers.tour_public(tour, locale, _cats(db), op)
    nexts = catalog_service.next_departures(db, [tour.id])
    data["next_departure"] = nexts.get(tour.id).isoformat() if nexts.get(tour.id) else None
    return data


@router.get("/tours/{slug}/departures")
def tour_departures(
    slug: str,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    db: Session = Depends(get_db),
):
    tour = _published(db, slug)
    start = date_from or today_local()
    end = date_to or (start + timedelta(days=31))
    if (end - start).days > 92:
        end = start + timedelta(days=92)
    deps = catalog_service.public_departures(db, tour, start, end)
    min_seats = platform_settings.low_availability_min_seats(db)
    return [serializers.departure_public(d, min_seats) for d in deps]


@router.post("/quotes")
def quote(body: QuoteIn, locale: str = Depends(locale_param), db: Session = Depends(get_db)):
    dep = db.get(Departure, body.departure_id)
    if not dep:
        raise not_found("Saída")
    tour = db.get(Tour, dep.tour_id)
    if tour.status != "published":
        raise not_found("Passeio")
    q = pricing.quote(tour, dep.starts_at.astimezone(TZ).date(), body.quantities, locale)
    return {
        "departure_id": dep.id,
        "lines": [{"code": line.code, "label": line.label, "quantity": line.quantity,
                   "unit_price_cents": line.unit_price_cents, "total_cents": line.total_cents} for line in q.lines],
        "pax_total": q.pax_total,
        "subtotal_cents": q.subtotal_cents,
        "service_fee_cents": 0,
        "total_cents": q.subtotal_cents,
    }


@router.get("/geocode", dependencies=[Depends(rate_limit("geocode", 30, 60))])
def geocode(q: str = Query(..., min_length=3, max_length=200), locale: str = Depends(locale_param)):
    return geocoding.geocode(q, locale)


@router.get("/sitemap")
def sitemap(db: Session = Depends(get_db)):
    """Dados para o sitemap do frontend (passeios publicados e categorias)."""
    tours = db.execute(
        select(Tour.slug, Tour.updated_at)
        .join(Operator, Operator.id == Tour.operator_id)
        .where(Tour.status == "published", Operator.status == "active")
    ).all()
    cats = db.scalars(select(Category.slug)).all()
    return {
        "tours": [{"slug": s, "updated_at": u.isoformat()} for s, u in tours],
        "categories": list(cats),
    }
