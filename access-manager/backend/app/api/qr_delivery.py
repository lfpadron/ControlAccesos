from __future__ import annotations

import base64
from datetime import UTC, datetime
import hmac
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.flow import (
    CitasOperationalReadUser, CitasOperationalWriteUser, PacientesReadUser, PacientesWriteUser,
    business_today, patient_display_name,
)
from app.core.config import get_settings
from app.core.database import get_db
from app.models.flow import Cita, Paciente, QrToken
from app.models.usuario import Usuario
from app.schemas.qr_delivery import (
    QrPreview, QrSendRequest, QrSendResponse, TelegramContactStatus, TelegramPatientStatus,
)
from app.services.access_scope import ensure_cita_access, ensure_paciente_access
from app.services import qr_delivery as delivery
from app.services.qr_service import encode_qr_payload, get_active_qr_payload, now_utc, token_digest

router = APIRouter()


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def delivery_context(db: Session, cita_id: UUID, user: Usuario) -> tuple[Cita, Paciente]:
    ensure_cita_access(db, user, cita_id, business_today())
    cita = db.scalar(select(Cita).where(Cita.id == cita_id).with_for_update().execution_options(populate_existing=True))
    if cita is None:
        raise HTTPException(404, "La cita no existe.")
    if cita.estado in {"CANCELADA", "EXPIRADA", "NO_LLEGO"}:
        raise HTTPException(409, "No se puede compartir el QR de una cita cancelada, expirada o no presentada.")
    patient = db.scalar(select(Paciente).where(Paciente.id == cita.paciente_id).with_for_update().execution_options(populate_existing=True))
    if patient is None or not patient.activo or patient.marcado_borrado_en is not None:
        raise HTTPException(409, "El paciente no está activo.")
    return cita, patient


@router.post("/citas/{cita_id}/qr/preparar", response_model=QrPreview)
def prepare_qr(cita_id: UUID, db: Session = Depends(get_db), current_user: Usuario = CitasOperationalReadUser):
    cita, patient = delivery_context(db, cita_id, current_user)
    qr_token, payload = get_active_qr_payload(db, cita)
    png = delivery.render_qr_png(payload, delivery.qr_details(db, cita))
    response = QrPreview(
        qr_id=qr_token.id, imagen_base64=base64.b64encode(png).decode("ascii"),
        nombre_archivo=delivery.qr_filename(cita), fecha_expiracion=utc(qr_token.fecha_expiracion),
        paciente=patient_display_name(patient) or patient.folio_paciente,
        cita_estado=cita.estado,
        cita_updated_at=utc(cita.updated_at), paciente_updated_at=utc(patient.updated_at),
        destinos=delivery.destinations(patient), metodo_preferido=patient.metodo_confirmacion,
        telegram_bot_url=delivery.telegram_bot_url(),
    )
    db.commit()
    return response


@router.post("/citas/{cita_id}/qr/enviar", response_model=QrSendResponse)
def send_qr(cita_id: UUID, payload: QrSendRequest, db: Session = Depends(get_db), current_user: Usuario = CitasOperationalWriteUser):
    cita, patient = delivery_context(db, cita_id, current_user)
    if utc(cita.updated_at) != utc(payload.cita_updated_at) or utc(patient.updated_at) != utc(payload.paciente_updated_at):
        raise HTTPException(409, "La cita o los datos de contacto cambiaron. Actualiza el QR y vuelve a seleccionar el destino.")
    destination = next((item for item in delivery.destinations(patient) if item.metodo == payload.metodo), None)
    if destination is None or not destination.disponible:
        raise HTTPException(409, destination.motivo if destination else "El paciente no tiene ese medio de contacto.")
    qr = db.scalar(select(QrToken).where(QrToken.id == payload.qr_id, QrToken.cita_id == cita.id).with_for_update())
    if qr is None or qr.estado != "GENERADO" or utc(qr.fecha_expiracion) <= now_utc():
        raise HTTPException(409, "El QR ya no está vigente. Actualiza el QR antes de enviarlo.")
    token = encode_qr_payload(cita, qr.fecha_emision, qr.fecha_expiracion)
    if token_digest(token) != qr.token_hash:
        raise HTTPException(409, "La cita cambió. Actualiza el QR antes de enviarlo.")
    details = delivery.qr_details(db, cita)
    png = delivery.render_qr_png(token, details)
    try:
        if payload.metodo == "CORREO":
            delivery.send_email(patient.correo_electronico, png, delivery.qr_filename(cita), details)
            message = "Correo aceptado para envío. Esto no confirma su recepción."
        else:
            position = int(payload.metodo[-1])
            delivery.send_telegram(getattr(patient, f"telegram_chat_id_{position}"), png, delivery.qr_filename(cita), details)
            message = "QR enviado por Telegram."
    except delivery.DeliveryError as exc:
        raise HTTPException(exc.status_code, str(exc)) from None
    # The short provider request runs under the appointment/contact locks. No
    # delivery record is created; cancellation cannot interleave with dispatch.
    db.commit()
    return QrSendResponse(mensaje=message)


def patient_status(patient: Paciente) -> TelegramPatientStatus:
    return TelegramPatientStatus(
        bot_url=delivery.telegram_bot_url(),
        contactos=[TelegramContactStatus(posicion=position, etiqueta=delivery.phone_label(position, phone), vinculado=bool(chat))
                   for position, phone, chat in delivery.mobile_contacts(patient)],
    )


@router.get("/pacientes/{paciente_id}/telegram", response_model=TelegramPatientStatus)
def get_patient_telegram(paciente_id: UUID, db: Session = Depends(get_db), current_user: Usuario = PacientesReadUser):
    ensure_paciente_access(db, current_user, paciente_id, business_today())
    patient = db.get(Paciente, paciente_id)
    if patient is None:
        raise HTTPException(404, "El paciente no existe.")
    return patient_status(patient)


@router.delete("/pacientes/{paciente_id}/telegram/{position}", response_model=TelegramPatientStatus)
def unlink_patient_telegram(paciente_id: UUID, position: int = Path(ge=1, le=2), db: Session = Depends(get_db), current_user: Usuario = PacientesWriteUser):
    ensure_paciente_access(db, current_user, paciente_id, business_today())
    patient = db.scalar(select(Paciente).where(Paciente.id == paciente_id).with_for_update())
    if patient is None:
        raise HTTPException(404, "El paciente no existe.")
    setattr(patient, f"telegram_chat_id_{position}", None)
    db.commit()
    return patient_status(patient)


@router.post("/telegram/webhook", include_in_schema=False)
def telegram_webhook(payload: dict, x_telegram_bot_api_secret_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    secret = get_settings().telegram_webhook_secret
    if not secret or not x_telegram_bot_api_secret_token or not hmac.compare_digest(secret.encode(), x_telegram_bot_api_secret_token.encode()):
        raise HTTPException(403, "Webhook no autorizado.")
    try:
        delivery.handle_telegram_update(db, payload)
    except delivery.DeliveryError as exc:
        raise HTTPException(exc.status_code, str(exc)) from None
    return {"ok": True}
