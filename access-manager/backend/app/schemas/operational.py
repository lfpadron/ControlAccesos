from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RoleCreate(BaseModel):
    codigo: str = Field(min_length=1, max_length=80)
    nombre: str = Field(min_length=1, max_length=180)
    descripcion: str | None = None
    activo: bool = True


class RoleUpdate(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=80)
    nombre: str | None = Field(default=None, min_length=1, max_length=180)
    descripcion: str | None = None
    activo: bool | None = None


class RoleRead(RoleCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UsuarioRolCreate(BaseModel):
    usuario_id: UUID
    rol_id: UUID
    institucion_id: UUID | None = None
    complejo_id: UUID | None = None
    activo: bool = True


class UsuarioRolUpdate(BaseModel):
    usuario_id: UUID | None = None
    rol_id: UUID | None = None
    institucion_id: UUID | None = None
    complejo_id: UUID | None = None
    activo: bool | None = None


class UsuarioRolRead(UsuarioRolCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PisoCreate(BaseModel):
    complejo_id: UUID
    numero: str = Field(min_length=1, max_length=40)
    nombre_visible: str = Field(min_length=1, max_length=180)
    descripcion: str | None = None
    activo: bool = True


class PisoUpdate(BaseModel):
    complejo_id: UUID | None = None
    numero: str | None = Field(default=None, min_length=1, max_length=40)
    nombre_visible: str | None = Field(default=None, min_length=1, max_length=180)
    descripcion: str | None = None
    activo: bool | None = None


class PisoRead(PisoCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SalaEsperaCreate(BaseModel):
    complejo_id: UUID
    piso_id: UUID
    nombre: str = Field(min_length=1, max_length=180)
    descripcion: str | None = None
    capacidad_estimada: int | None = Field(default=None, ge=0)
    activa: bool = True


class SalaEsperaUpdate(BaseModel):
    complejo_id: UUID | None = None
    piso_id: UUID | None = None
    nombre: str | None = Field(default=None, min_length=1, max_length=180)
    descripcion: str | None = None
    capacidad_estimada: int | None = Field(default=None, ge=0)
    activa: bool | None = None


class SalaEsperaRead(SalaEsperaCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConsultorioCreate(BaseModel):
    complejo_id: UUID
    piso_id: UUID
    codigo: str = Field(min_length=1, max_length=80)
    nombre_visible: str | None = Field(default=None, max_length=180)
    instrucciones_acceso: str | None = None
    cluster_ids: list[UUID] = Field(default_factory=list)
    activo: bool = True


class ConsultorioUpdate(BaseModel):
    complejo_id: UUID | None = None
    piso_id: UUID | None = None
    codigo: str | None = Field(default=None, min_length=1, max_length=80)
    nombre_visible: str | None = Field(default=None, max_length=180)
    instrucciones_acceso: str | None = None
    cluster_ids: list[UUID] | None = None
    activo: bool | None = None


class ConsultorioRead(ConsultorioCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClusterTurnosCreate(BaseModel):
    complejo_id: UUID
    piso_id: UUID
    nombre: str = Field(min_length=1, max_length=180)
    descripcion: str | None = None
    activo: bool = True


class ClusterTurnosUpdate(BaseModel):
    complejo_id: UUID | None = None
    piso_id: UUID | None = None
    nombre: str | None = Field(default=None, min_length=1, max_length=180)
    descripcion: str | None = None
    activo: bool | None = None


class ClusterTurnosRead(ClusterTurnosCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MedicoCreate(BaseModel):
    usuario_id: UUID | None = None
    nombre: str = Field(min_length=1, max_length=180)
    apellidos: str = Field(min_length=1, max_length=180)
    nombre_visible: str | None = Field(default=None, max_length=220)
    activo: bool = True


class MedicoUpdate(BaseModel):
    usuario_id: UUID | None = None
    nombre: str | None = Field(default=None, min_length=1, max_length=180)
    apellidos: str | None = Field(default=None, min_length=1, max_length=180)
    nombre_visible: str | None = Field(default=None, max_length=220)
    activo: bool | None = None


class MedicoRead(MedicoCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OperadorCreate(BaseModel):
    usuario_id: UUID
    activo: bool = True


class OperadorUpdate(BaseModel):
    usuario_id: UUID | None = None
    activo: bool | None = None


class OperadorRead(OperadorCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DateRangeMixin(BaseModel):
    fecha_inicio: date
    fecha_fin: date | None = None

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.fecha_fin is not None and self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser menor que fecha_inicio")
        return self


class AsignacionMedicoConsultorioCreate(DateRangeMixin):
    medico_id: UUID
    consultorio_id: UUID
    hora_inicio: time | None = None
    hora_fin: time | None = None
    dias_semana: str | None = Field(default=None, max_length=120)
    activo: bool = True


class AsignacionMedicoConsultorioUpdate(BaseModel):
    medico_id: UUID | None = None
    consultorio_id: UUID | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    hora_inicio: time | None = None
    hora_fin: time | None = None
    dias_semana: str | None = Field(default=None, max_length=120)
    activo: bool | None = None


class AsignacionMedicoConsultorioRead(AsignacionMedicoConsultorioCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AsignacionOperadorCreate(DateRangeMixin):
    operador_id: UUID
    medico_id: UUID | None = None
    consultorio_id: UUID | None = None
    complejo_id: UUID
    prioridad: int = Field(default=100, ge=1)
    activo: bool = True

    @model_validator(mode="after")
    def validate_destination(self):
        super().validate_date_range()
        if self.medico_id is None and self.consultorio_id is None:
            raise ValueError("Debe indicar médico o consultorio para la asignación")
        return self


class AsignacionOperadorUpdate(BaseModel):
    operador_id: UUID | None = None
    medico_id: UUID | None = None
    consultorio_id: UUID | None = None
    complejo_id: UUID | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    prioridad: int | None = Field(default=None, ge=1)
    activo: bool | None = None


class AsignacionOperadorRead(AsignacionOperadorCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditoriaRead(BaseModel):
    id: UUID
    evento: str
    entidad: str
    entidad_id: UUID | None
    usuario_id: UUID | None
    canal: str | None
    ip_origen: str | None
    valor_antes: dict | None
    valor_despues: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
