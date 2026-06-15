from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PuntoAccesoCreate(BaseModel):
    complejo_id: UUID
    piso_id: UUID
    nombre: str = Field(min_length=1, max_length=180)
    descripcion: str | None = None
    activo: bool = True


class PuntoAccesoUpdate(BaseModel):
    complejo_id: UUID | None = None
    piso_id: UUID | None = None
    nombre: str | None = Field(default=None, min_length=1, max_length=180)
    descripcion: str | None = None
    activo: bool | None = None


class PuntoAccesoRead(PuntoAccesoCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KioskoConfigMixin(BaseModel):
    polling_interval_seconds: int = Field(default=5, ge=2, le=30)
    color_fondo: str | None = Field(default=None, max_length=40)
    color_texto: str | None = Field(default=None, max_length=40)
    color_primario: str | None = Field(default=None, max_length=40)
    color_acento: str | None = Field(default=None, max_length=40)


class KioskoCreate(KioskoConfigMixin):
    codigo_dispositivo: str = Field(min_length=1, max_length=120)
    token: str = Field(min_length=8, max_length=128)
    complejo_id: UUID
    piso_id: UUID
    punto_acceso_id: UUID
    nombre: str | None = Field(default=None, max_length=180)
    descripcion: str | None = None
    activo: bool = True


class KioskoUpdate(BaseModel):
    codigo_dispositivo: str | None = Field(default=None, min_length=1, max_length=120)
    token: str | None = Field(default=None, min_length=8, max_length=128)
    complejo_id: UUID | None = None
    piso_id: UUID | None = None
    punto_acceso_id: UUID | None = None
    nombre: str | None = Field(default=None, max_length=180)
    descripcion: str | None = None
    activo: bool | None = None
    polling_interval_seconds: int | None = Field(default=None, ge=2, le=30)
    color_fondo: str | None = Field(default=None, max_length=40)
    color_texto: str | None = Field(default=None, max_length=40)
    color_primario: str | None = Field(default=None, max_length=40)
    color_acento: str | None = Field(default=None, max_length=40)


class KioskoRead(KioskoConfigMixin):
    id: UUID
    codigo_dispositivo: str
    complejo_id: UUID
    piso_id: UUID
    punto_acceso_id: UUID
    nombre: str | None
    descripcion: str | None
    activo: bool
    ultima_conexion: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
