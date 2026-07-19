from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.password_policy import validate_user_password


class UsuarioCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=180)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    telefono: str | None = Field(default=None, max_length=64)
    two_factor_enabled: bool = False
    force_password_change: bool = False
    estado: str = Field(default="ACTIVO", max_length=32)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_user_password(value)


class UsuarioUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=180)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    telefono: str | None = Field(default=None, max_length=64)
    two_factor_enabled: bool | None = None
    force_password_change: bool | None = None
    estado: str | None = Field(default=None, max_length=32)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str | None) -> str | None:
        return validate_user_password(value)


class UsuarioRead(BaseModel):
    id: UUID
    nombre: str
    email: EmailStr
    telefono: str | None
    two_factor_enabled: bool
    force_password_change: bool
    estado: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
