from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ComplejoBase(BaseModel):
    institucion_id: UUID
    nombre: str = Field(min_length=1, max_length=180)
    descripcion: str | None = None
    logo_url: str | None = Field(default=None, max_length=500)
    direccion: str | None = None
    telefono: str | None = Field(default=None, max_length=64)
    zona_horaria: str = Field(default="America/Mexico_City", max_length=64)
    color_primario: str | None = Field(default=None, max_length=32)
    color_secundario: str | None = Field(default=None, max_length=32)
    color_acento: str | None = Field(default=None, max_length=32)
    activo: bool = True


class ComplejoCreate(ComplejoBase):
    pass


class ComplejoUpdate(BaseModel):
    institucion_id: UUID | None = None
    nombre: str | None = Field(default=None, min_length=1, max_length=180)
    descripcion: str | None = None
    logo_url: str | None = Field(default=None, max_length=500)
    direccion: str | None = None
    telefono: str | None = Field(default=None, max_length=64)
    zona_horaria: str | None = Field(default=None, max_length=64)
    color_primario: str | None = Field(default=None, max_length=32)
    color_secundario: str | None = Field(default=None, max_length=32)
    color_acento: str | None = Field(default=None, max_length=32)
    activo: bool | None = None


class ComplejoRead(ComplejoBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
