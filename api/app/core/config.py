"""Configuração central. Tudo vem de variáveis de ambiente (12-factor)."""
from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "Tur"
    secret_key: str
    frontend_url: str = "http://localhost:5173"
    api_public_url: str = "http://localhost:8000"
    allowed_hosts: str = "localhost,127.0.0.1"

    database_url: str
    db_pool_size: int = 10
    db_max_overflow: int = 20
    redis_url: str = "redis://localhost:6379/0"

    auth_enabled: bool = False
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    admin_email: str = "admin@tur.local"
    admin_name: str = "Admin"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "Tur <no-reply@tur.local>"
    smtp_tls: bool = True

    payment_gateway: str = "fake"
    payment_api_key: str = ""
    payment_webhook_secret: str = ""
    payment_env: str = "sandbox"

    storage_endpoint: str = ""
    storage_bucket: str = ""
    storage_access_key: str = ""
    storage_secret_key: str = ""
    storage_public_url: str = ""
    media_dir: str = "media"

    geocoding_provider: Literal["photon", "nominatim"] = "photon"
    geocoding_user_agent: str = "tur-dev"

    sentry_dsn: str = ""
    log_level: str = "INFO"

    max_body_bytes: int = 8 * 1024 * 1024
    max_upload_bytes: int = 5 * 1024 * 1024

    @field_validator("secret_key")
    @classmethod
    def _secret_len(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY precisa ter pelo menos 32 caracteres")
        return v

    @model_validator(mode="after")
    def _production_guards(self) -> "Settings":
        if self.app_env == "production":
            if not self.auth_enabled:
                raise ValueError("AUTH_ENABLED=false é proibido em produção")
            if self.payment_gateway == "fake":
                raise ValueError("PAYMENT_GATEWAY=fake é proibido em produção")
            if self.secret_key.startswith("dev-"):
                raise ValueError("Troque o SECRET_KEY de desenvolvimento em produção")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def frontend_urls(self) -> list[str]:
        return [u.strip().rstrip("/") for u in self.frontend_url.split(",") if u.strip()]

    @property
    def primary_frontend_url(self) -> str:
        return self.frontend_urls[0] if self.frontend_urls else "http://localhost:5173"

    @property
    def allowed_host_list(self) -> list[str]:
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]

    @property
    def google_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret and self.google_redirect_uri)

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host)

    @property
    def storage_configured(self) -> bool:
        return bool(self.storage_bucket and self.storage_access_key and self.storage_secret_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
