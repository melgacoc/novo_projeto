from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import normalize_phone


class QuoteIn(BaseModel):
    departure_id: int
    quantities: dict[str, int]

    @field_validator("quantities")
    @classmethod
    def _q(cls, v: dict[str, int]) -> dict[str, int]:
        if any(q < 0 or q > 200 for q in v.values()):
            raise ValueError("Quantidade inválida")
        return v


class BookingCreate(QuoteIn):
    contact_name: str = Field(min_length=2, max_length=160)
    contact_phone: str
    locale: str = "pt"
    source: str | None = Field(None, max_length=120)

    @field_validator("contact_phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        return normalize_phone(v)


class PaymentCreate(BaseModel):
    method: str
    idempotency_key: str | None = Field(None, max_length=80)


class AdminCancelIn(BaseModel):
    reason: str = Field("admin", max_length=40)
    refund_cents: int | None = Field(None, ge=0)


class EmailCodeRequest(BaseModel):
    email: EmailStr
    locale: str = "pt"


class EmailCodeVerify(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)
    locale: str = "pt"


class MePatch(BaseModel):
    name: str | None = Field(None, max_length=160)
    phone: str | None = None
    locale: str | None = None

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        return normalize_phone(v) if v else v

    @field_validator("locale")
    @classmethod
    def _loc(cls, v: str | None) -> str | None:
        if v is not None and v not in ("pt", "es", "en"):
            raise ValueError("Idioma inválido")
        return v
