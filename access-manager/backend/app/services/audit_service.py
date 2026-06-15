from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models.auditoria import Auditoria


def record_audit_event(
    db: Session,
    *,
    evento: str,
    entidad: str,
    entidad_id: UUID | None = None,
    usuario_id: UUID | None = None,
    canal: str | None = None,
    ip_origen: str | None = None,
    valor_antes: dict | None = None,
    valor_despues: dict | None = None,
) -> Auditoria:
    audit = Auditoria(
        evento=evento,
        entidad=entidad,
        entidad_id=entidad_id,
        usuario_id=usuario_id,
        canal=canal,
        ip_origen=ip_origen,
        valor_antes=valor_antes,
        valor_despues=valor_despues,
    )
    db.add(audit)
    return audit


def audit_safe_dict(model: object) -> dict:
    hidden_fields = {"password", "password_hash", "access_token", "token", "token_hash"}
    payload: dict = {}
    mapper = inspect(model.__class__)
    for column in mapper.columns:
        key = column.key
        if key in hidden_fields:
            continue
        value = getattr(model, key)
        if isinstance(value, UUID):
            payload[key] = str(value)
        elif isinstance(value, (datetime, date, time)):
            payload[key] = value.isoformat()
        else:
            payload[key] = value
    return payload
