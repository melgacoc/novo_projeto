from datetime import date

from geoalchemy2 import Geography
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

LOCALES = ("pt", "es", "en")
TOUR_STATUSES = ("draft", "pending_review", "published", "paused", "rejected")
CANCELLATION_POLICIES = ("flexible", "moderate", "strict")
PRICE_CATEGORY_CODES = ("adult", "child", "infant", "senior")


class Category(TimestampMixin, Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    name_pt: Mapped[str] = mapped_column(String(80))
    name_es: Mapped[str] = mapped_column(String(80))
    name_en: Mapped[str] = mapped_column(String(80))
    icon: Mapped[str] = mapped_column(String(40), default="map-pin")
    position: Mapped[int] = mapped_column(Integer, default=0)


class Tour(TimestampMixin, Base):
    __tablename__ = "tours"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey("operators.id"), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=240)
    min_pax_per_booking: Mapped[int] = mapped_column(Integer, default=1)
    max_pax_per_booking: Mapped[int] = mapped_column(Integer, default=10)
    # região aproximada (pública) e ponto de encontro exato (privado, só no voucher)
    public_location = mapped_column(Geography("POINT", srid=4326), nullable=True)
    public_area_label: Mapped[str] = mapped_column(String(120), default="")
    # cópias em float para leitura simples (a busca usa as colunas geográficas)
    public_lat: Mapped[float | None] = mapped_column(Float)
    public_lng: Mapped[float | None] = mapped_column(Float)
    meeting_lat: Mapped[float | None] = mapped_column(Float)
    meeting_lng: Mapped[float | None] = mapped_column(Float)
    meeting_point_location = mapped_column(Geography("POINT", srid=4326), nullable=True)
    meeting_point_address: Mapped[str] = mapped_column(String(255), default="")
    booking_cutoff_minutes: Mapped[int] = mapped_column(Integer, default=120)
    instant_booking: Mapped[bool] = mapped_column(Boolean, default=True)
    cancellation_policy: Mapped[str] = mapped_column(String(20), default="flexible")
    on_site_fees_note: Mapped[str] = mapped_column(String(255), default="")
    # menor preço de adulto vigente, desnormalizado para busca e ordenação
    from_price_cents: Mapped[int | None] = mapped_column(Integer, index=True)
    rating_avg: Mapped[float | None] = mapped_column(Numeric(3, 2))
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    review_notes: Mapped[str] = mapped_column(Text, default="")

    translations: Mapped[list["TourTranslation"]] = relationship(
        back_populates="tour", cascade="all, delete-orphan", lazy="selectin"
    )
    photos: Mapped[list["TourPhoto"]] = relationship(
        back_populates="tour", cascade="all, delete-orphan", order_by="TourPhoto.position", lazy="selectin"
    )
    price_categories: Mapped[list["TourPriceCategory"]] = relationship(
        back_populates="tour", cascade="all, delete-orphan", lazy="selectin"
    )


class TourTranslation(TimestampMixin, Base):
    __tablename__ = "tour_translations"
    __table_args__ = (UniqueConstraint("tour_id", "locale"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id", ondelete="CASCADE"), index=True)
    locale: Mapped[str] = mapped_column(String(5))
    title: Mapped[str] = mapped_column(String(160), default="")
    summary: Mapped[str] = mapped_column(String(300), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    includes: Mapped[str] = mapped_column(Text, default="")
    excludes: Mapped[str] = mapped_column(Text, default="")
    what_to_bring: Mapped[str] = mapped_column(Text, default="")
    # privado: instruções do ponto de encontro (só no voucher)
    meeting_point_details: Mapped[str] = mapped_column(Text, default="")

    tour: Mapped[Tour] = relationship(back_populates="translations")


class TourPhoto(TimestampMixin, Base):
    __tablename__ = "tour_photos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(500))
    storage_key: Mapped[str] = mapped_column(String(300), default="")
    position: Mapped[int] = mapped_column(Integer, default=0)
    alt: Mapped[str] = mapped_column(String(200), default="")

    tour: Mapped[Tour] = relationship(back_populates="photos")


class TourPriceCategory(TimestampMixin, Base):
    __tablename__ = "tour_price_categories"
    __table_args__ = (UniqueConstraint("tour_id", "code"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(20))
    min_age: Mapped[int] = mapped_column(Integer, default=0)
    max_age: Mapped[int] = mapped_column(Integer, default=120)
    label_pt: Mapped[str] = mapped_column(String(60), default="")
    label_es: Mapped[str] = mapped_column(String(60), default="")
    label_en: Mapped[str] = mapped_column(String(60), default="")

    tour: Mapped[Tour] = relationship(back_populates="price_categories")
    prices: Mapped[list["TourPrice"]] = relationship(
        back_populates="category", cascade="all, delete-orphan", order_by="TourPrice.valid_from", lazy="selectin"
    )


class TourPrice(TimestampMixin, Base):
    __tablename__ = "tour_prices"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    price_category_id: Mapped[int] = mapped_column(
        ForeignKey("tour_price_categories.id", ondelete="CASCADE"), index=True
    )
    price_cents: Mapped[int] = mapped_column(Integer)
    valid_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)

    category: Mapped[TourPriceCategory] = relationship(back_populates="prices")
