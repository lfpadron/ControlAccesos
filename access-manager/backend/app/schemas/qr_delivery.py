from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


DeliveryMethod = Literal["CORREO", "TELEGRAM_1", "TELEGRAM_2"]


class QrDestination(BaseModel):
    metodo: DeliveryMethod
    etiqueta: str
    disponible: bool
    motivo: str | None = None
    vinculable: bool = False


class QrPreview(BaseModel):
    qr_id: UUID
    imagen_base64: str
    nombre_archivo: str
    fecha_expiracion: datetime
    paciente: str
    cita_estado: str
    cita_updated_at: datetime
    paciente_updated_at: datetime
    destinos: list[QrDestination]
    metodo_preferido: str | None = None
    telegram_bot_url: str | None = None


class QrSendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metodo: DeliveryMethod
    qr_id: UUID
    cita_updated_at: datetime
    paciente_updated_at: datetime


class QrSendResponse(BaseModel):
    mensaje: str


class TelegramContactStatus(BaseModel):
    posicion: Literal[1, 2]
    etiqueta: str
    vinculado: bool


class TelegramPatientStatus(BaseModel):
    bot_url: str | None
    contactos: list[TelegramContactStatus]
