from __future__ import annotations

from app.core.config import Settings


def test_database_url_uses_psycopg_driver_for_plain_postgresql_urls() -> None:
    settings = Settings(DATABASE_URL="postgresql://user:pass@db.example.com/access_manager")

    assert settings.database_url == "postgresql+psycopg://user:pass@db.example.com/access_manager"


def test_database_url_uses_psycopg_driver_for_postgres_urls() -> None:
    settings = Settings(DATABASE_URL="postgres://user:pass@db.example.com/access_manager")

    assert settings.database_url == "postgresql+psycopg://user:pass@db.example.com/access_manager"


def test_database_url_keeps_explicit_driver() -> None:
    settings = Settings(DATABASE_URL="postgresql+psycopg://user:pass@db.example.com/access_manager")

    assert settings.database_url == "postgresql+psycopg://user:pass@db.example.com/access_manager"
