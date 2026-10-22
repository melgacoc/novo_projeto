"""Conversão de modelos em JSON por público (turista, operadora, admin).
Dados privados da operadora (contato, ponto de encontro exato) nunca saem nas visões públicas (RN10)."""
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Booking, Category, Departure, Operator, Payment, Tour, TourSchedule, User
from app.services import pricing
from app.services.catalog_service import availability_label, category_name, tour_text
from app.services.schedule_service import TZ


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _photo(tour: Tour) -> str | None:
    return tour.photos[0].url if tour.photos else None


def user_me(user: User, operators: list[Operator]) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "phone": user.phone_e164,
        "role": user.role,
        "locale": user.locale,
        "is_dev_user": user.is_dev_user,
        "operators": [{"id": o.id, "public_name": o.public_name, "status": o.status} for o in operators],
    }


def category(cat: Category, locale: str) -> dict:
    return {"id": cat.id, "slug": cat.slug, "name": category_name(cat, locale), "icon": cat.icon,
            "name_pt": cat.name_pt, "name_es": cat.name_es, "name_en": cat.name_en, "position": cat.position}


def tour_card(tour: Tour, locale: str, cats: dict[int, Category], operator: Operator | None,
              next_departure: datetime | None = None, distance_m: float | None = None) -> dict:
    t = tour_text(tour, locale)
    cat = cats.get(tour.category_id) if tour.category_id else None
    return {
        "id": tour.id,
        "slug": tour.slug,
        "title": t.title,
        "summary": t.summary,
        "category": category(cat, locale) if cat else None,
        "area": tour.public_area_label,
        "lat": tour.public_lat,
        "lng": tour.public_lng,
        "from_price_cents": tour.from_price_cents,
        "duration_minutes": tour.duration_minutes,
        "photo": _photo(tour),
        "rating_avg": float(tour.rating_avg) if tour.rating_avg is not None else None,
        "rating_count": tour.rating_count,
        "operator_name": operator.public_name if operator else None,
        "next_departure": _iso(next_departure),
        "distance_m": round(distance_m) if distance_m is not None else None,
    }


def tour_public(tour: Tour, locale: str, cats: dict[int, Category], operator: Operator) -> dict:
    t = tour_text(tour, locale)
    today = datetime.now(TZ).date()
    price_categories = []
    for c in sorted(tour.price_categories, key=lambda c: ["adult", "senior", "child", "infant"].index(c.code)):
        price_categories.append({
            "code": c.code,
            "label": pricing.label(c, locale),
            "min_age": c.min_age,
            "max_age": c.max_age,
            "price_cents_today": pricing.price_on(c, today),
        })
    data = tour_card(tour, locale, cats, operator)
    data.update({
        "description": t.description,
        "includes": t.includes,
        "excludes": t.excludes,
        "what_to_bring": t.what_to_bring,
        "photos": [{"url": p.url, "alt": p.alt} for p in tour.photos],
        "price_categories": price_categories,
        "min_pax_per_booking": tour.min_pax_per_booking,
        "max_pax_per_booking": tour.max_pax_per_booking,
        "booking_cutoff_minutes": tour.booking_cutoff_minutes,
        "cancellation_policy": tour.cancellation_policy,
        "on_site_fees_note": tour.on_site_fees_note,
        "instant_booking": tour.instant_booking,
        "available_locales": sorted({tr.locale for tr in tour.translations if tr.title}),
    })
    return data


def departure_public(dep: Departure, min_seats: int) -> dict:
    local = dep.starts_at.astimezone(TZ)
    return {
        "id": dep.id,
        "starts_at": _iso(dep.starts_at),
        "date": local.date().isoformat(),
        "time": local.strftime("%H:%M"),
        "availability": availability_label(dep, min_seats),
    }


def departure_operator(dep: Departure) -> dict:
    local = dep.starts_at.astimezone(TZ)
    return {
        "id": dep.id,
        "tour_id": dep.tour_id,
        "schedule_id": dep.schedule_id,
        "starts_at": _iso(dep.starts_at),
        "date": local.date().isoformat(),
        "time": local.strftime("%H:%M"),
        "capacity": dep.capacity,
        "seats_held": dep.seats_held,
        "seats_booked": dep.seats_booked,
        "seats_available": dep.seats_available,
        "status": dep.status,
        "cancel_reason": dep.cancel_reason,
        "manually_edited": dep.manually_edited,
    }


def schedule(s: TourSchedule) -> dict:
    return {"id": s.id, "weekdays": s.weekdays, "start_time": s.start_time.strftime("%H:%M"),
            "capacity": s.capacity, "valid_from": s.valid_from.isoformat(),
            "valid_to": s.valid_to.isoformat() if s.valid_to else None}


def tour_full(tour: Tour, db: Session) -> dict:
    """Visão completa para a operadora dona e para o admin."""
    schedules = db.scalars(select(TourSchedule).where(TourSchedule.tour_id == tour.id).order_by(TourSchedule.id)).all()
    return {
        "id": tour.id,
        "operator_id": tour.operator_id,
        "slug": tour.slug,
        "status": tour.status,
        "category_id": tour.category_id,
        "duration_minutes": tour.duration_minutes,
        "min_pax_per_booking": tour.min_pax_per_booking,
        "max_pax_per_booking": tour.max_pax_per_booking,
        "public_area_label": tour.public_area_label,
        "public_lat": tour.public_lat,
        "public_lng": tour.public_lng,
        "meeting_point_address": tour.meeting_point_address,
        "meeting_lat": tour.meeting_lat,
        "meeting_lng": tour.meeting_lng,
        "booking_cutoff_minutes": tour.booking_cutoff_minutes,
        "instant_booking": tour.instant_booking,
        "cancellation_policy": tour.cancellation_policy,
        "on_site_fees_note": tour.on_site_fees_note,
        "from_price_cents": tour.from_price_cents,
        "review_notes": tour.review_notes,
        "translations": [
            {k: getattr(tr, k) for k in ("locale", "title", "summary", "description", "includes", "excludes",
                                         "what_to_bring", "meeting_point_details")}
            for tr in sorted(tour.translations, key=lambda x: ("pt", "es", "en").index(x.locale))
        ],
        "photos": [{"id": p.id, "url": p.url, "position": p.position, "alt": p.alt} for p in tour.photos],
        "price_categories": [
            {
                "code": c.code, "min_age": c.min_age, "max_age": c.max_age,
                "label_pt": c.label_pt, "label_es": c.label_es, "label_en": c.label_en,
                "prices": [{"price_cents": p.price_cents, "valid_from": p.valid_from.isoformat(),
                            "valid_to": p.valid_to.isoformat() if p.valid_to else None} for p in c.prices],
            }
            for c in tour.price_categories
        ],
        "schedules": [schedule(s) for s in schedules],
        "title": tour_text(tour, "pt").title,
        "created_at": _iso(tour.created_at),
        "updated_at": _iso(tour.updated_at),
    }


def payment(p: Payment) -> dict:
    return {
        "id": p.id, "method": p.method, "status": p.status, "amount_cents": p.amount_cents,
        "gateway": p.gateway, "charge_id": p.gateway_charge_id, "pix_qr_code": p.pix_qr_code,
        "pix_expires_at": _iso(p.pix_expires_at), "checkout_url": p.checkout_url,
    }


def booking(b: Booking, db: Session, *, audience: str) -> dict:
    """audience: tourist | operator | admin."""
    data = {
        "code": b.code,
        "status": b.status,
        "tour_id": b.tour_id,
        "tour_slug": b.snapshot.get("tour_slug"),
        "title": b.snapshot.get("title"),
        "area": b.snapshot.get("area"),
        "starts_at": b.snapshot.get("starts_at"),
        "duration_minutes": b.snapshot.get("duration_minutes"),
        "operator_name": b.snapshot.get("operator_name"),
        "cancellation_policy": b.snapshot.get("cancellation_policy"),
        "on_site_fees_note": b.snapshot.get("on_site_fees_note"),
        "pax_total": b.pax_total,
        "items": [{"code": i.price_category_code, "label": i.label, "quantity": i.quantity,
                   "unit_price_cents": i.unit_price_cents} for i in b.items],
        "total_cents": b.total_cents,
        "refund_amount_cents": b.refund_amount_cents,
        "hold_expires_at": _iso(b.hold_expires_at),
        "paid_at": _iso(b.paid_at),
        "confirmed_at": _iso(b.confirmed_at),
        "cancelled_at": _iso(b.cancelled_at),
        "cancelled_by": b.cancelled_by,
        "cancel_reason": b.cancel_reason,
        "locale": b.locale,
        "contact_name": b.contact_name,
        "created_at": _iso(b.created_at),
    }
    payments = db.scalars(select(Payment).where(Payment.booking_id == b.id).order_by(Payment.id)).all()
    data["payments"] = [payment(p) for p in payments]
    if audience in ("operator", "admin"):
        data.update({
            "contact_phone": b.contact_phone_e164,
            "contact_email": b.contact_email,
            "commission_rate": float(b.commission_rate),
            "commission_cents": b.commission_cents,
            "operator_amount_cents": b.operator_amount_cents,
            "operator_id": b.operator_id,
            "departure_id": b.departure_id,
            "source": b.source,
            "no_show_at": _iso(b.no_show_at),
            "completed_at": _iso(b.completed_at),
        })
    # dados privados da operadora só depois da confirmação (RN10)
    if audience == "tourist" and b.status in ("confirmed", "completed", "no_show"):
        tour = db.get(Tour, b.tour_id)
        op = db.get(Operator, b.operator_id)
        t = tour_text(tour, b.locale)
        data["private"] = {
            "meeting_point_address": tour.meeting_point_address,
            "meeting_point_details": t.meeting_point_details,
            "meeting_lat": tour.meeting_lat,
            "meeting_lng": tour.meeting_lng,
            "operator_trade_name": op.trade_name,
            "operator_phone": op.contact_phone,
            "operator_email": op.contact_email,
        }
    return data


def operator_admin(o: Operator, default_rate) -> dict:
    return {
        "id": o.id, "public_name": o.public_name, "trade_name": o.trade_name, "legal_name": o.legal_name,
        "document": o.document, "cadastur_number": o.cadastur_number, "status": o.status,
        "commission_rate": float(o.commission_rate) if o.commission_rate is not None else None,
        "effective_commission_rate": float(o.commission_rate if o.commission_rate is not None else default_rate),
        "contact_phone": o.contact_phone, "contact_email": o.contact_email,
        "cancellations_count": o.cancellations_count, "notes": o.notes,
        "gateway_recipient_id": o.gateway_recipient_id, "created_at": _iso(o.created_at),
    }


def date_iso(d: date | None) -> str | None:
    return d.isoformat() if d else None
