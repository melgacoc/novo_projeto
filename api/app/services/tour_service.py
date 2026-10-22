"""Cadastro de passeios (operadora e admin em modo concierge), fotos e regras de publicação (RN13)."""
import re
import unicodedata
from io import BytesIO

from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.config import settings
from app.core.errors import AppError, bad_request, conflict
from app.models import Tour, TourPhoto, TourPrice, TourPriceCategory, TourTranslation
from app.schemas.tour import TourIn
from app.services import moderation, pricing, storage
from app.services.catalog_service import set_locations
from app.services.schedule_service import today_local

MAX_PHOTOS = 12


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:100] or "passeio"


def unique_slug(db: Session, base: str, tour_id: int | None = None) -> str:
    slug, n = base, 2
    while True:
        existing = db.scalar(select(Tour.id).where(Tour.slug == slug))
        if existing is None or existing == tour_id:
            return slug
        slug = f"{base}-{n}"
        n += 1


def apply_input(db: Session, tour: Tour, data: TourIn) -> None:
    for field in ("category_id", "duration_minutes", "min_pax_per_booking", "max_pax_per_booking",
                  "public_area_label", "meeting_point_address", "booking_cutoff_minutes",
                  "cancellation_policy", "on_site_fees_note"):
        setattr(tour, field, getattr(data, field))
    set_locations(tour, data.meeting_lat, data.meeting_lng)

    by_locale = {t.locale: t for t in tour.translations}
    for tr in data.translations:
        row = by_locale.get(tr.locale)
        if not row:
            row = TourTranslation(locale=tr.locale)
            tour.translations.append(row)
        for k, v in tr.model_dump().items():
            setattr(row, k, v)

    # categorias de preço: substitui o conjunto (preços antigos ficam congelados nas reservas)
    tour.price_categories.clear()
    db.flush()
    for c in data.price_categories:
        cat = TourPriceCategory(
            code=c.code, min_age=c.min_age, max_age=c.max_age,
            label_pt=c.label_pt, label_es=c.label_es, label_en=c.label_en,
        )
        for p in c.prices:
            cat.prices.append(TourPrice(price_cents=p.price_cents, valid_from=p.valid_from, valid_to=p.valid_to))
        tour.price_categories.append(cat)
    db.flush()
    pricing.recompute_from_price(tour, today_local())

    pt = next((t for t in data.translations if t.locale == "pt" and t.title), None)
    any_title = pt or next((t for t in data.translations if t.title), None)
    if any_title and (not tour.slug or tour.status == "draft"):
        tour.slug = unique_slug(db, slugify(any_title.title), tour.id)
    if not tour.slug:
        tour.slug = unique_slug(db, f"passeio-{tour.operator_id}")


def create(db: Session, operator_id: int, data: TourIn, actor_id: int | None) -> Tour:
    tour = Tour(operator_id=operator_id, status="draft", slug="")
    db.add(tour)
    db.flush()
    apply_input(db, tour, data)
    audit(db, actor_id, "tour", tour.id, "create")
    db.commit()
    return tour


def update(db: Session, tour: Tour, data: TourIn, actor_id: int | None) -> Tour:
    old = {"status": tour.status, "from_price_cents": tour.from_price_cents}
    apply_input(db, tour, data)
    audit(db, actor_id, "tour", tour.id, "update", old, {"from_price_cents": tour.from_price_cents})
    db.commit()
    return tour


def publication_problems(tour: Tour) -> list[str]:
    """RN13: 3 idiomas, foto, preço vigente, agenda, local."""
    problems = []
    by = {t.locale: t for t in tour.translations}
    for loc in ("pt", "es", "en"):
        t = by.get(loc)
        if not t or not t.title or not t.summary or not t.description:
            problems.append(f"missing_text_{loc}")
    if not tour.photos:
        problems.append("missing_photo")
    if tour.from_price_cents is None:
        problems.append("missing_price")
    if tour.category_id is None:
        problems.append("missing_category")
    if tour.meeting_lat is None:
        problems.append("missing_location")
    return problems


def contact_flags(tour: Tour) -> list[dict]:
    texts = {}
    for t in tour.translations:
        for f in ("title", "summary", "description", "includes", "excludes", "what_to_bring"):
            texts[f"{t.locale}.{f}"] = getattr(t, f)
    texts["public_area_label"] = tour.public_area_label
    return moderation.find_contact_flags(texts)


def submit(db: Session, tour: Tour, has_schedule: bool, actor_id: int | None) -> Tour:
    problems = publication_problems(tour)
    if not has_schedule:
        problems.append("missing_schedule")
    if problems:
        raise bad_request("not_ready", "O passeio ainda não pode ser publicado", {"problems": problems})
    if tour.status not in ("draft", "rejected", "paused"):
        raise conflict("invalid_status", "O passeio já está em análise ou publicado")
    tour.status = "pending_review"
    audit(db, actor_id, "tour", tour.id, "submit")
    db.commit()
    return tour


def set_status(db: Session, tour: Tour, status: str, actor_id: int | None, notes: str = "") -> Tour:
    if status == "published":
        problems = publication_problems(tour)
        if problems:
            raise bad_request("not_ready", "O passeio não cumpre os requisitos de publicação", {"problems": problems})
    old = tour.status
    tour.status = status
    if notes:
        tour.review_notes = notes
    audit(db, actor_id, "tour", tour.id, "status", {"status": old}, {"status": status, "notes": notes})
    db.commit()
    return tour


def add_photo(db: Session, tour: Tour, content: bytes, alt: str) -> TourPhoto:
    if len(tour.photos) >= MAX_PHOTOS:
        raise conflict("too_many_photos", f"Máximo de {MAX_PHOTOS} fotos")
    if len(content) > settings.max_upload_bytes:
        raise AppError(413, "file_too_large", "Arquivo muito grande (máx. 5 MB)")
    if not storage.sniff_image_type(content):
        raise bad_request("invalid_image", "Envie uma imagem JPG, PNG ou WebP")
    # reprocessa a imagem: valida de verdade, remove metadados (EXIF/GPS) e limita o tamanho
    try:
        img = Image.open(BytesIO(content))
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise bad_request("invalid_image", "Imagem inválida") from exc
    img = img.convert("RGB")
    img.thumbnail((1920, 1920))
    out = BytesIO()
    img.save(out, format="JPEG", quality=85, optimize=True)
    key, url = storage.save_image(out.getvalue(), "image/jpeg", f"tours/{tour.id}")
    photo = TourPhoto(tour_id=tour.id, url=url, storage_key=key, position=len(tour.photos), alt=alt[:200])
    tour.photos.append(photo)
    db.commit()
    return photo


def delete_photo(db: Session, tour: Tour, photo_id: int) -> None:
    photo = next((p for p in tour.photos if p.id == photo_id), None)
    if not photo:
        raise AppError(404, "not_found", "Foto não encontrada")
    storage.delete(photo.storage_key)
    tour.photos.remove(photo)
    for i, p in enumerate(tour.photos):
        p.position = i
    db.commit()


def reorder_photos(db: Session, tour: Tour, ids: list[int]) -> None:
    pos = {pid: i for i, pid in enumerate(ids)}
    for p in tour.photos:
        p.position = pos.get(p.id, len(ids) + p.position)
    db.commit()
