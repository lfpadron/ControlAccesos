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
ESTADOS_ATENCION_MEDICO = {"AUSENTE", "NO_DISPONIBLE", "EN_CONSULTA", "DISPONIBLE", "NO_MOSTRAR"}


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
    medico_id: UUID


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
    medico_ids: list[UUID] = Field(default_factory=list)
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
    duracion_estimada: int = Field(default=60, ge=1, le=720)
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
    medico_estado_atencion: str = "DISPONIBLE"
    medico_notas_estado: str | None = None


class MedicoEstadoRead(BaseModel):
    id: UUID
    usuario_id: UUID | None = None
    nombre: str
    apellidos: str
    nombre_visible: str | None = None
    estado_atencion: str
    notas_estado: str | None = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MedicoEstadoUpdate(BaseModel):
    estado_atencion: str = Field(max_length=32)
    notas_estado: str | None = Field(default=None, max_length=100)

    @field_validator("notas_estado", mode="before")
    @classmethod
    def blank_note_to_none(cls, value):
        if isinstance(value, str):
            text = value.strip()
            return text or None
        return value

    @model_validator(mode="after")
    def validate_estado(self):
        if self.estado_atencion not in ESTADOS_ATENCION_MEDICO:
            raise ValueError("Estado de médico inválido.")
        return self


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
    requiere_confirmacion: bool = False
    fecha_label: str | None = None
    torre: str | None = None
    piso: str | None = None
    checkin_at: datetime | None = None


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
    requiere_confirmacion: bool = False
    fecha_label: str | None = None
    torre: str | None = None
    piso: str | None = None
    checkin_at: datetime | None = None


class ReceptionOption(BaseModel):
    id: UUID
    label: str


class ReceptionOptions(BaseModel):
    pacientes: list[ReceptionOption]
    medicos: list[ReceptionOption]
    consultorios: list[ReceptionOption]


class ReceptionCitaItem(BaseModel):
    id: UUID
    estado: str
    paciente_id: UUID
    paciente: str
    fecha_cita: date
    hora_cita: time
    consultorio_id: UUID
    consultorio: str
    torre: str
    piso_id: UUID
    piso: str
    medico_id: UUID
    medico: str
    checkin_at: datetime | None = None
    can_cancel_checkin: bool = False


class ReceptionCitasResponse(BaseModel):
    items: list[ReceptionCitaItem]
    total: int
    limit: int
    offset: int


class ReceptionCheckinCancelResponse(BaseModel):
    cancelado: bool
    mensaje: str
    cita_id: UUID
    estado_cita: str


class TicketResponse(BaseModel):
    encabezado_fecha: str
    leyenda: str
    turno: str
    qr_payload: str
    consultorio: str
    torre: str
    piso: str
    hora: str


class MobileSessionResponse(BaseModel):
    usuario_id: UUID
    nombre: str
    email: str
    roles: list[str]
    can_checkin: bool
    can_view_logs: bool


class CitaActionResponse(BaseModel):
    id: UUID
    estado: str
    folio_turno: str


class ReportePacienteItem(BaseModel):
    paciente_id: UUID
    folio_paciente: str
    paciente: str
    medico: str | None = None
    fecha_ultima_cita: date | None = None
    hora_ultima_cita: time | None = None
    se_presento: bool | None = None


class ReporteCitaItem(BaseModel):
    cita_id: UUID
    fecha_cita: date
    hora_cita: time
    paciente: str
    medico: str
    campus: str
    torre: str
    piso: str
    consultorio: str
    estado: str
    se_presento: bool


class ReporteAgrupadoItem(BaseModel):
    periodo: str
    citas: int


class ReporteHorarioItem(BaseModel):
    fecha: date
    dia_semana: str
    horas: dict[str, int]
    total: int


class ReporteRecepcionAgrupadoItem(BaseModel):
    campus_id: UUID
    campus: str
    torre_id: UUID
    torre: str
    piso_id: UUID
    piso: str
    periodo: str
    citas: int


class ReporteRecepcionHorarioItem(BaseModel):
    campus_id: UUID
    campus: str
    torre_id: UUID
    torre: str
    piso_id: UUID
    piso: str
    fecha: date
    dia_semana: str
    horas: dict[str, int]
    total: int
