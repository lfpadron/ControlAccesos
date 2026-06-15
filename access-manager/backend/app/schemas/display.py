from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PantallaTurnosConfigMixin(BaseModel):
    polling_interval_seconds: int = Field(default=5, ge=2, le=10)
    color_fondo: str | None = Field(default=None, max_length=40)
    color_texto: str | None = Field(default=None, max_length=40)
    color_turno_nuevo: str | None = Field(default=None, max_length=40)
    color_turno_normal: str | None = Field(default=None, max_length=40)
    font_size_turno_nuevo: int | None = Field(default=None, ge=24, le=220)
    font_size_turno_normal: int | None = Field(default=None, ge=18, le=160)
    segundos_resaltado: int = Field(default=25, ge=5, le=120)
    segundos_visible: int = Field(default=300, ge=30, le=3600)
    max_turnos_visibles: int = Field(default=10, ge=1, le=50)


class PantallaTurnosCreate(PantallaTurnosConfigMixin):
    codigo_dispositivo: str = Field(min_length=1, max_length=120)
    token: str | None = Field(default=None, min_length=8, max_length=128)
    complejo_id: UUID
    piso_id: UUID | None = None
    cluster_espera_id: UUID | None = None
    cluster_ids: list[UUID] = Field(min_length=1)
    consultorio_id: UUID | None = None
    nombre: str | None = Field(default=None, max_length=180)
    descripcion: str | None = Field(default=None, max_length=1000)
    activa: bool = True


class PantallaTurnosUpdate(BaseModel):
    codigo_dispositivo: str | None = Field(default=None, min_length=1, max_length=120)
    token: str | None = Field(default=None, min_length=8, max_length=128)
    complejo_id: UUID | None = None
    piso_id: UUID | None = None
    cluster_espera_id: UUID | None = None
    cluster_ids: list[UUID] | None = Field(default=None, min_length=1)
    consultorio_id: UUID | None = None
    nombre: str | None = Field(default=None, max_length=180)
    descripcion: str | None = Field(default=None, max_length=1000)
    activa: bool | None = None
    polling_interval_seconds: int | None = Field(default=None, ge=2, le=10)
    color_fondo: str | None = Field(default=None, max_length=40)
    color_texto: str | None = Field(default=None, max_length=40)
    color_turno_nuevo: str | None = Field(default=None, max_length=40)
    color_turno_normal: str | None = Field(default=None, max_length=40)
    font_size_turno_nuevo: int | None = Field(default=None, ge=24, le=220)
    font_size_turno_normal: int | None = Field(default=None, ge=18, le=160)
    segundos_resaltado: int | None = Field(default=None, ge=5, le=120)
    segundos_visible: int | None = Field(default=None, ge=30, le=3600)
    max_turnos_visibles: int | None = Field(default=None, ge=1, le=50)


class PantallaTurnosRead(PantallaTurnosConfigMixin):
    id: UUID
    codigo_dispositivo: str
    complejo_id: UUID
    piso_id: UUID | None
    cluster_espera_id: UUID | None
    cluster_ids: list[UUID]
    consultorio_id: UUID | None
    nombre: str | None
    descripcion: str | None
    activa: bool
    ultima_conexion: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PantallaTurnosPublicConfig(PantallaTurnosConfigMixin):
    pass


class PublicTurnoDisplay(BaseModel):
    turno: str
    consultorio: str
    estado: str
    llamado_en: datetime
    resaltado: bool


class PublicDisplayResponse(BaseModel):
    codigo_dispositivo: str
    ultima_conexion: datetime
    config: PantallaTurnosPublicConfig
    turnos: list[PublicTurnoDisplay]


class TurnoDisplayRecienteRead(BaseModel):
    turno: str
    consultorio: str
    llamado_en: datetime
    estado: str


class CitaLlamarResponse(BaseModel):
    id: UUID
    turno: str
    consultorio: str
    estado: str
    llamado_en: datetime
    resaltado_hasta: datetime
    visible_hasta: datetime
