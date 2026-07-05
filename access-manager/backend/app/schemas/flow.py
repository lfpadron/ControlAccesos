from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


TIPOS_CITA = {"PROGRAMADA", "ESPONTANEA"}
ESTADOS_CITA = {
    "AGENDADA",
    "QR_GENERADO",
    "LLEGO_LOBBY",
    "AUTORIZADO_PASAR",
    "EN_CONSULTA",
    "FINALIZADA",
    "NO_LLEGO",
    "CANCELADA",
    "EXPIRADA",
}
CHECKIN_CANALES = {"KIOSKO", "RECEPCION", "OPERADOR", "APP_MOVIL", "BOT_TELEGRAM", "API_EXTERNA"}


class PacienteBase(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=180)
    nombre_preferido: str | None = Field(default=None, max_length=60)
    apellido_paterno: str | None = Field(default=None, min_length=1, max_length=180)
    apellido_materno: str | None = Field(default=None, max_length=180)
    celular: str | None = Field(default=None, max_length=40)
    fecha_nacimiento: date | None = None
    activo: bool = True

    @field_validator("nombre", "nombre_preferido", "apellido_paterno", "apellido_materno", "celular", mode="before")
    @classmethod
    def blank_to_none(cls, value):
        if isinstance(value, str):
            text = value.strip()
            return text or None
        return value

    @model_validator(mode="after")
    def validate_values(self):
        if not self.nombre_preferido and not (self.nombre and self.apellido_paterno):
            raise ValueError("Debe indicar nombre preferido o nombre y apellido paterno.")
        if not self.celular and self.fecha_nacimiento is None:
            raise ValueError("Debe indicar celular o fecha de nacimiento.")
        return self


class PacienteCreate(PacienteBase):
    pass


class PacienteUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=180)
    nombre_preferido: str | None = Field(default=None, max_length=60)
    apellido_paterno: str | None = Field(default=None, min_length=1, max_length=180)
    apellido_materno: str | None = Field(default=None, max_length=180)
    celular: str | None = Field(default=None, max_length=40)
    fecha_nacimiento: date | None = None
    activo: bool | None = None

    @field_validator("nombre", "nombre_preferido", "apellido_paterno", "apellido_materno", "celular", mode="before")
    @classmethod
    def blank_to_none(cls, value):
        if isinstance(value, str):
            text = value.strip()
            return text or None
        return value


class PacienteRead(PacienteBase):
    id: UUID
    folio_paciente: str
    desactivado_en: datetime | None = None
    marcado_borrado_en: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CitaBase(BaseModel):
    tipo: str = Field(default="PROGRAMADA")
    estado: str = Field(default="AGENDADA")
    paciente_id: UUID
    medico_id: UUID
    consultorio_id: UUID
    complejo_id: UUID
    piso_id: UUID
    sala_prevista_id: UUID | None = None
    fecha_cita: date
    hora_cita: time
    duracion_estimada: int | None = Field(default=None, ge=1, le=720)
    origen: str | None = Field(default=None, max_length=80)
    notas_operativas: str | None = None

    @model_validator(mode="after")
    def validate_values(self):
        if self.tipo not in TIPOS_CITA:
            raise ValueError("Tipo de cita inválido.")
        if self.estado not in ESTADOS_CITA:
            raise ValueError("Estado de cita inválido.")
        return self


class CitaCreate(CitaBase):
    estado: str = "AGENDADA"


class CitaUpdate(BaseModel):
    tipo: str | None = None
    estado: str | None = None
    paciente_id: UUID | None = None
    medico_id: UUID | None = None
    consultorio_id: UUID | None = None
    complejo_id: UUID | None = None
    piso_id: UUID | None = None
    sala_prevista_id: UUID | None = None
    fecha_cita: date | None = None
    hora_cita: time | None = None
    duracion_estimada: int | None = Field(default=None, ge=1, le=720)
    origen: str | None = Field(default=None, max_length=80)
    notas_operativas: str | None = None

    @model_validator(mode="after")
    def validate_values(self):
        if self.tipo is not None and self.tipo not in TIPOS_CITA:
            raise ValueError("Tipo de cita inválido.")
        if self.estado is not None and self.estado not in ESTADOS_CITA:
            raise ValueError("Estado de cita inválido.")
        return self


class CitaRead(BaseModel):
    id: UUID
    tipo: str
    estado: str
    paciente_id: UUID
    medico_id: UUID
    consultorio_id: UUID
    complejo_id: UUID
    piso_id: UUID
    sala_prevista_id: UUID | None
    fecha_cita: date
    hora_cita: time
    duracion_estimada: int | None
    folio_turno: str
    origen: str | None
    notas_operativas: str | None
    creada_por: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CitaListItem(CitaRead):
    paciente: str | None = None
    paciente_nombre_completo: str | None = None
    consultorio: str | None = None
    piso: str | None = None
    medico: str | None = None


class CitaSearchResult(BaseModel):
    id: UUID
    folio_turno: str
    hora_cita: time
    consultorio: str | None = None
    piso: str | None = None
    estado: str


class QrGenerateResponse(BaseModel):
    id: UUID
    cita_id: UUID
    estado: str
    fecha_emision: datetime
    fecha_expiracion: datetime
    qr_payload: str


class QrRead(BaseModel):
    id: UUID
    cita_id: UUID
    estado: str
    fecha_emision: datetime
    fecha_expiracion: datetime

    model_config = ConfigDict(from_attributes=True)


class QrValidarRequest(BaseModel):
    token: str = Field(min_length=12)


class QrValidarResponse(BaseModel):
    valido: bool
    resultado: str
    mensaje: str
    cita_id: UUID | None = None
    folio_turno: str | None = None
    estado_cita: str | None = None


class CheckinRequest(BaseModel):
    canal: str = "RECEPCION"
    sala_id: UUID | None = None
    dispositivo_id: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_channel(self):
        if self.canal not in CHECKIN_CANALES:
            raise ValueError("Canal de check-in inválido.")
        return self


class QrCheckinRequest(BaseModel):
    token: str = Field(min_length=12)
    canal: str = "KIOSKO"
    sala_id: UUID | None = None
    dispositivo_id: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_channel(self):
        if self.canal not in CHECKIN_CANALES:
            raise ValueError("Canal de check-in inválido.")
        return self


class CheckinResponse(BaseModel):
    resultado: str
    mensaje: str
    cita_id: UUID | None = None
    folio_turno: str | None = None
    estado_cita: str | None = None


class TicketResponse(BaseModel):
    encabezado_fecha: str
    leyenda: str
    turno: str
    qr_payload: str
    consultorio: str
    piso: str
    hora: str


class CitaActionResponse(BaseModel):
    id: UUID
    estado: str
    folio_turno: str
