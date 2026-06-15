from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InstitucionBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    razon_social: str | None = Field(default=None, max_length=120)
    notas: str | None = Field(default=None, max_length=500)
    logo_url: str | None = Field(default=None, max_length=500)
    color_primario: str | None = Field(default=None, max_length=32)
    color_secundario: str | None = Field(default=None, max_length=32)
    color_acento: str | None = Field(default=None, max_length=32)
    activo: bool = True


class InstitucionCreate(InstitucionBase):
    pass


class InstitucionUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    razon_social: str | None = Field(default=None, max_length=120)
    notas: str | None = Field(default=None, max_length=500)
    logo_url: str | None = Field(default=None, max_length=500)
    color_primario: str | None = Field(default=None, max_length=32)
    color_secundario: str | None = Field(default=None, max_length=32)
    color_acento: str | None = Field(default=None, max_length=32)
    activo: bool | None = None


class InstitucionRead(InstitucionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
