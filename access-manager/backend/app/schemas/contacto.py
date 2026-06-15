from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

MEDIO_TIPOS = {"CELULAR", "CORREO"}
CONTACTO_TIPOS = {"PRIMARIO", "SECUNDARIO", "SOLO_EMERGENCIAS", "OTRO"}


class MedioContacto(BaseModel):
    tipo: str
    valor: str = Field(min_length=1, max_length=180)

    @model_validator(mode="after")
    def validate_tipo(self):
        if self.tipo not in MEDIO_TIPOS:
            raise ValueError("Tipo de medio inválido.")
        return self


class ContactoInstitucionalBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=180)
    medios_contacto: list[MedioContacto] = Field(min_length=2, max_length=5)
    tipo_contacto: str
    tipo_contacto_descripcion: str | None = Field(default=None, max_length=50)
    notas: str | None = Field(default=None, max_length=1000)
    complejo_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_tipo_contacto(self):
        if self.tipo_contacto not in CONTACTO_TIPOS:
            raise ValueError("Tipo de contacto inválido.")
        if self.tipo_contacto == "OTRO" and not (self.tipo_contacto_descripcion or "").strip():
            raise ValueError("Debe describir el tipo de contacto.")
        return self


class ContactoInstitucionalCreate(ContactoInstitucionalBase):
    pass


class ContactoInstitucionalUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=180)
    medios_contacto: list[MedioContacto] | None = Field(default=None, min_length=2, max_length=5)
    tipo_contacto: str | None = None
    tipo_contacto_descripcion: str | None = Field(default=None, max_length=50)
    notas: str | None = Field(default=None, max_length=1000)
    complejo_ids: list[UUID] | None = None

    @model_validator(mode="after")
    def validate_tipo_contacto(self):
        if self.tipo_contacto is not None and self.tipo_contacto not in CONTACTO_TIPOS:
            raise ValueError("Tipo de contacto inválido.")
        if self.tipo_contacto == "OTRO" and not (self.tipo_contacto_descripcion or "").strip():
            raise ValueError("Debe describir el tipo de contacto.")
        return self


class ContactoInstitucionalRead(BaseModel):
    id: UUID
    nombre: str
    medios_contacto: list[MedioContacto]
    tipo_contacto: str
    tipo_contacto_descripcion: str | None
    notas: str | None
    complejo_ids: list[UUID]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
