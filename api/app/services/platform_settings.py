from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import PlatformSetting
from app.models.platform import DEFAULT_SETTINGS


def get_setting(db: Session, key: str) -> str:
    row = db.get(PlatformSetting, key)
    if row:
        return row.value
    return DEFAULT_SETTINGS[key]


def get_all(db: Session) -> dict[str, str]:
    return {k: get_setting(db, k) for k in DEFAULT_SETTINGS}


def set_setting(db: Session, key: str, value: str) -> None:
    row = db.get(PlatformSetting, key)
    if row:
        row.value = value
    else:
        db.add(PlatformSetting(key=key, value=value))


def default_commission_rate(db: Session) -> Decimal:
    return Decimal(get_setting(db, "default_commission_rate"))


def hold_minutes(db: Session) -> int:
    return int(get_setting(db, "hold_minutes"))


def payout_delay_days(db: Session) -> int:
    return int(get_setting(db, "payout_delay_days"))


def low_availability_min_seats(db: Session) -> int:
    return int(get_setting(db, "low_availability_min_seats"))
