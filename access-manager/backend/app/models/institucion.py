from __future__ import annotations

from typing import TYPE_CHECKING
import uuid

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.complejo import Complejo


class Institucion(TimestampMixin, Base):
    __tablename__ = "instituciones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    razon_social: Mapped[str | None] = mapped_column(String(120))
    notas: Mapped[str | None] = mapped_column(String(500))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    color_primario: Mapped[str | None] = mapped_column(String(32))
    color_secundario: Mapped[str | None] = mapped_column(String(32))
    color_acento: Mapped[str | None] = mapped_column(String(32))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

    complejos: Mapped[list[Complejo]] = relationship("Complejo", back_populates="institucion")
