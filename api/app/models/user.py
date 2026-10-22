from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin

ROLES = ("tourist", "operator", "admin")


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), default="")
    phone_e164: Mapped[str | None] = mapped_column(String(20))
    role: Mapped[str] = mapped_column(String(20), default="tourist")
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    locale: Mapped[str] = mapped_column(String(5), default="pt")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # usuários fixos do modo sem login (AUTH_ENABLED=false)
    is_dev_user: Mapped[bool] = mapped_column(Boolean, default=False)


class EmailLoginCode(TimestampMixin, Base):
    __tablename__ = "email_login_codes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RefreshToken(TimestampMixin, Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    # tokens da mesma "família" vêm de rotações sucessivas; reuso de um token antigo revoga a família
    family: Mapped[str] = mapped_column(String(64), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_id: Mapped[int | None] = mapped_column(BigInteger)
