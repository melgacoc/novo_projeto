import phonenumbers
from pydantic import BaseModel, ConfigDict, field_validator


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def normalize_phone(value: str) -> str:
    """E.164. Sem DDI, assume Brasil; estrangeiros com + ou 00."""
    raw = value.strip()
    if raw.startswith("00"):
        raw = "+" + raw[2:]
    try:
        num = phonenumbers.parse(raw, None if raw.startswith("+") else "BR")
    except phonenumbers.NumberParseException as exc:
        raise ValueError("Telefone inválido") from exc
    if not phonenumbers.is_possible_number(num):
        raise ValueError("Telefone inválido")
    return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)


class PhoneMixin(BaseModel):
    @field_validator("phone", check_fields=False)
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        return normalize_phone(v) if v else v


class Message(BaseModel):
    message: str
