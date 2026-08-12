from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.password_policy import validate_user_password


def normalize_optional_email(value: object) -> object:
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    return value


class UsuarioCreate(BaseModel):
    apellidos: str = Field(min_length=1, max_length=180)
    nombre: str = Field(min_length=1, max_length=180)
    email: EmailStr
    correo_alterno: EmailStr | None = Field(default=None, max_length=255)
    notas: str | None = Field(default=None, max_length=500)
    password: str = Field(min_length=8, max_length=128)
    telefono: str | None = Field(default=None, max_length=64)
    two_factor_enabled: bool = False
    force_password_change: bool = False
    estado: str = Field(default="ACTIVO", max_length=32)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_user_password(value)

    @field_validator("correo_alterno", mode="before")
    @classmethod
    def normalize_correo_alterno(cls, value: object) -> object:
        return normalize_optional_email(value)

    @field_validator("apellidos", "nombre", mode="before")
    @classmethod
    def normalize_required_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("notas", mode="before")
    @classmethod
    def normalize_notas(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value


class UsuarioUpdate(BaseModel):
    apellidos: str | None = Field(default=None, min_length=1, max_length=180)
    nombre: str | None = Field(default=None, min_length=1, max_length=180)
    email: EmailStr | None = None
    correo_alterno: EmailStr | None = Field(default=None, max_length=255)
    notas: str | None = Field(default=None, max_length=500)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    telefono: str | None = Field(default=None, max_length=64)
    two_factor_enabled: bool | None = None
    force_password_change: bool | None = None
    estado: str | None = Field(default=None, max_length=32)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str | None) -> str | None:
        return validate_user_password(value)

    @field_validator("correo_alterno", mode="before")
    @classmethod
    def normalize_correo_alterno(cls, value: object) -> object:
        return normalize_optional_email(value)

    @field_validator("apellidos", "nombre", mode="before")
    @classmethod
    def normalize_required_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("notas", mode="before")
    @classmethod
    def normalize_notas(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value


class UsuarioProfileUpdate(BaseModel):
    correo_alterno: EmailStr | None = Field(default=None, max_length=255)

    @field_validator("correo_alterno", mode="before")
    @classmethod
    def normalize_correo_alterno(cls, value: object) -> object:
        return normalize_optional_email(value)


class UsuarioRead(BaseModel):
    id: UUID
    apellidos: str
    nombre: str
    email: EmailStr
    correo_alterno: EmailStr | None
    notas: str | None
    telefono: str | None
    two_factor_enabled: bool
    force_password_change: bool
    estado: str
    roles: list[str] = Field(default_factory=list)
    role_codes: list[str] = Field(default_factory=list)
    permisos: dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
