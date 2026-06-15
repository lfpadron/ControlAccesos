from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Access Manager API"
    app_version: str = Field(default="0.2.0", alias="APP_VERSION")
    environment: str = "local"
    log_level: str = "INFO"
    database_url: str = Field(
        default="postgresql+psycopg://access_manager:access_manager@postgres:5432/access_manager",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    jwt_secret: str = Field(default="change-me-local-dev-only", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=480, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    qr_signing_secret: str | None = Field(default=None, alias="QR_SIGNING_SECRET")
    qr_expiration_hours: int = Field(default=24, alias="QR_EXPIRATION_HOURS")
    checkin_green_before_minutes: int = Field(default=120, alias="CHECKIN_GREEN_BEFORE_MINUTES")
    checkin_green_after_minutes: int = Field(default=30, alias="CHECKIN_GREEN_AFTER_MINUTES")
    checkin_yellow_before_minutes: int = Field(default=240, alias="CHECKIN_YELLOW_BEFORE_MINUTES")
    seed_admin_password: str | None = Field(default=None, alias="SEED_ADMIN_PASSWORD")
    cors_origins: str = Field(default="http://localhost:8080,http://127.0.0.1:8080", alias="CORS_ORIGINS")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def qr_secret(self) -> str:
        return self.qr_signing_secret or self.jwt_secret


@lru_cache
def get_settings() -> Settings:
    return Settings()
