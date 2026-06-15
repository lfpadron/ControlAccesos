from __future__ import annotations

from fastapi import APIRouter, Depends
from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db

router = APIRouter()


def root_health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "service": "access-manager-api", "version": settings.app_version}


@router.get("/health")
def api_health(db: Session = Depends(get_db)) -> dict[str, str]:
    settings = get_settings()
    db.execute(text("select 1"))
    Redis.from_url(settings.redis_url, socket_timeout=1).ping()
    return {"status": "ok", "service": "access-manager-api", "version": settings.app_version, "database": "ok", "redis": "ok"}
