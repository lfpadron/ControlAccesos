from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
import hashlib
import hmac
import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.flow import Cita, QrToken


@dataclass(frozen=True)
class QrValidationResult:
    valid: bool
    status: str
    message: str
    cita: Cita | None = None
    qr_token: QrToken | None = None


def now_utc() -> datetime:
    return datetime.now(UTC)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(f"{data}{padding}".encode("ascii"))


def _signature(payload: dict[str, str]) -> str:
    settings = get_settings()
    signing_input = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(settings.qr_secret.encode("utf-8"), signing_input, hashlib.sha256).hexdigest()


def encode_qr_payload(cita: Cita, emitido: datetime, expira: datetime) -> str:
    payload = {
        "cita_id": str(cita.id),
        "folio_turno": cita.folio_turno,
        "emitido": emitido.isoformat(),
        "expira": expira.isoformat(),
    }
    payload["firma"] = _signature(payload)
    return _b64encode(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def decode_qr_payload(token: str) -> dict[str, str]:
    return json.loads(_b64decode(token))


def qr_expiration_for_cita(cita: Cita, emitido: datetime) -> datetime:
    settings = get_settings()
    end_of_day = datetime.combine(cita.fecha_cita, time(23, 59, 59), tzinfo=UTC)
    configured = emitido + timedelta(hours=settings.qr_expiration_hours)
    return max(end_of_day, configured)


def generate_qr(db: Session, cita: Cita) -> tuple[QrToken, str]:
    timestamp = now_utc()
    expiration = qr_expiration_for_cita(cita, timestamp)
    db.execute(
        QrToken.__table__.update()
        .where(QrToken.cita_id == cita.id, QrToken.estado == "GENERADO")
        .values(estado="CANCELADO", updated_at=timestamp)
    )
    token = encode_qr_payload(cita, timestamp, expiration)
    qr_token = QrToken(
        cita_id=cita.id,
        estado="GENERADO",
        token_hash=token_digest(token),
        fecha_emision=timestamp,
        fecha_expiracion=expiration,
    )
    db.add(qr_token)
    cita.estado = "QR_GENERADO" if cita.estado == "AGENDADA" else cita.estado
    db.flush()
    return qr_token, token


def cancel_qr(db: Session, cita_id: UUID) -> int:
    timestamp = now_utc()
    result = db.execute(
        QrToken.__table__.update()
        .where(QrToken.cita_id == cita_id, QrToken.estado == "GENERADO")
        .values(estado="CANCELADO", updated_at=timestamp)
    )
    db.flush()
    return result.rowcount or 0


def validate_qr(db: Session, token: str) -> QrValidationResult:
    timestamp = now_utc()
    try:
        payload = decode_qr_payload(token)
        signature = payload.pop("firma")
    except Exception:
        return QrValidationResult(False, "ROJO", "El QR no tiene un formato válido.")

    expected_signature = _signature(payload)
    if not hmac.compare_digest(signature, expected_signature):
        return QrValidationResult(False, "ROJO", "La firma del QR no es válida.")

    try:
        cita_id = UUID(payload["cita_id"])
        expira = datetime.fromisoformat(payload["expira"])
    except Exception:
        return QrValidationResult(False, "ROJO", "El contenido del QR no es válido.")

    if expira <= timestamp:
        qr_token = db.execute(select(QrToken).where(QrToken.token_hash == token_digest(token))).scalar_one_or_none()
        if qr_token is not None and qr_token.estado == "GENERADO":
            qr_token.estado = "EXPIRADO"
            db.flush()
        return QrValidationResult(False, "ROJO", "El QR está expirado.", qr_token=qr_token)

    qr_token = db.execute(
        select(QrToken).where(
            QrToken.cita_id == cita_id,
            QrToken.token_hash == token_digest(token),
        )
    ).scalar_one_or_none()
    if qr_token is None:
        return QrValidationResult(False, "ROJO", "El QR no está registrado.")
    if qr_token.estado != "GENERADO":
        return QrValidationResult(False, "ROJO", f"El QR está en estado {qr_token.estado}.", qr_token=qr_token)
    if qr_token.fecha_expiracion <= timestamp:
        qr_token.estado = "EXPIRADO"
        db.flush()
        return QrValidationResult(False, "ROJO", "El QR está expirado.", qr_token=qr_token)

    cita = db.get(Cita, cita_id)
    if cita is None:
        return QrValidationResult(False, "ROJO", "La cita del QR no existe.", qr_token=qr_token)
    if cita.estado in {"CANCELADA", "EXPIRADA", "NO_LLEGO"}:
        return QrValidationResult(False, "ROJO", f"La cita está en estado {cita.estado}.", cita=cita, qr_token=qr_token)
    return QrValidationResult(True, "VERDE", "QR válido.", cita=cita, qr_token=qr_token)
