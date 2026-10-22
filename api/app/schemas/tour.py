from datetime import date, time

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.catalog import CANCELLATION_POLICIES, LOCALES, PRICE_CATEGORY_CODES


class TranslationIn(BaseModel):
    locale: str
    title: str = Field("", max_length=160)
    summary: str = Field("", max_length=300)
    description: str = Field("", max_length=8000)
    includes: str = Field("", max_length=3000)
    excludes: str = Field("", max_length=3000)
    what_to_bring: str = Field("", max_length=3000)
    meeting_point_details: str = Field("", max_length=2000)

    @field_validator("locale")
    @classmethod
    def _loc(cls, v: str) -> str:
        if v not in LOCALES:
            raise ValueError("Idioma inválido")
        return v


class PriceIn(BaseModel):
    price_cents: int = Field(ge=0, le=10_000_000)
    valid_from: date
    valid_to: date | None = None

    @model_validator(mode="after")
    def _range(self):
        if self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("valid_to antes de valid_from")
        return self


class PriceCategoryIn(BaseModel):
    code: str
    min_age: int = Field(0, ge=0, le=120)
    max_age: int = Field(120, ge=0, le=120)
    label_pt: str = ""
    label_es: str = ""
    label_en: str = ""
    prices: list[PriceIn] = []

    @field_validator("code")
    @classmethod
    def _code(cls, v: str) -> str:
        if v not in PRICE_CATEGORY_CODES:
            raise ValueError("Categoria inválida")
        return v

    @model_validator(mode="after")
    def _no_overlap(self):
        ps = sorted(self.prices, key=lambda p: p.valid_from)
        for a, b in zip(ps, ps[1:]):
            if a.valid_to is None or a.valid_to >= b.valid_from:
                raise ValueError(f"Vigências de preço sobrepostas em {self.code}")
        return self


class TourIn(BaseModel):
    category_id: int | None = None
    duration_minutes: int = Field(240, ge=15, le=24 * 60 * 3)
    min_pax_per_booking: int = Field(1, ge=1, le=100)
    max_pax_per_booking: int = Field(10, ge=1, le=200)
    public_area_label: str = Field("", max_length=120)
    meeting_point_address: str = Field("", max_length=255)
    meeting_lat: float | None = Field(None, ge=-90, le=90)
    meeting_lng: float | None = Field(None, ge=-180, le=180)
    booking_cutoff_minutes: int = Field(120, ge=0, le=7 * 24 * 60)
    cancellation_policy: str = "flexible"
    on_site_fees_note: str = Field("", max_length=255)
    translations: list[TranslationIn] = []
    price_categories: list[PriceCategoryIn] = []

    @field_validator("cancellation_policy")
    @classmethod
    def _policy(cls, v: str) -> str:
        if v not in CANCELLATION_POLICIES:
            raise ValueError("Política inválida")
        return v

    @model_validator(mode="after")
    def _pax(self):
        if self.max_pax_per_booking < self.min_pax_per_booking:
            raise ValueError("max_pax_per_booking menor que min_pax_per_booking")
        codes = [c.code for c in self.price_categories]
        if len(codes) != len(set(codes)):
            raise ValueError("Categoria de preço repetida")
        return self


class ScheduleIn(BaseModel):
    weekdays: list[int]
    start_time: time
    capacity: int = Field(ge=1, le=1000)
    valid_from: date
    valid_to: date | None = None

    @field_validator("weekdays")
    @classmethod
    def _wd(cls, v: list[int]) -> list[int]:
        if not v or any(d < 0 or d > 6 for d in v):
            raise ValueError("Dias da semana inválidos (0 = segunda ... 6 = domingo)")
        return sorted(set(v))


class DepartureIn(BaseModel):
    starts_at_local: str  # "YYYY-MM-DDTHH:MM" no fuso do Rio
    capacity: int = Field(ge=1, le=1000)


class DeparturePatch(BaseModel):
    capacity: int | None = Field(None, ge=0, le=1000)
    status: str | None = None

    @field_validator("status")
    @classmethod
    def _st(cls, v: str | None) -> str | None:
        if v is not None and v not in ("open", "closed"):
            raise ValueError("Use open ou closed; para cancelar, use a rota de cancelamento")
        return v


class CancelDepartureIn(BaseModel):
    reason: str = "weather"

    @field_validator("reason")
    @classmethod
    def _r(cls, v: str) -> str:
        if v not in ("weather", "operator", "other"):
            raise ValueError("Motivo inválido")
        return v
