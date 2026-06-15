from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UsuarioCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=180)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    telefono: str | None = Field(default=None, max_length=64)
    two_factor_enabled: bool = False
    estado: str = Field(default="ACTIVO", max_length=32)


class UsuarioUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=180)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    telefono: str | None = Field(default=None, max_length=64)
    two_factor_enabled: bool | None = None
    estado: str | None = Field(default=None, max_length=32)


class UsuarioRead(BaseModel):
    id: UUID
    nombre: str
    email: EmailStr
    telefono: str | None
    two_factor_enabled: bool
    estado: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
