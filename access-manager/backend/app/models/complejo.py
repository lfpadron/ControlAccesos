from __future__ import annotations

from typing import TYPE_CHECKING
import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.institucion import Institucion


class Complejo(TimestampMixin, Base):
    __tablename__ = "complejos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institucion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("instituciones.id"),
        nullable=False,
        index=True,
    )
    nombre: Mapped[str] = mapped_column(String(180), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    direccion: Mapped[str | None] = mapped_column(Text)
    telefono: Mapped[str | None] = mapped_column(String(64))
    zona_horaria: Mapped[str] = mapped_column(String(64), nullable=False, default="America/Mexico_City")
    color_primario: Mapped[str | None] = mapped_column(String(32))
    color_secundario: Mapped[str | None] = mapped_column(String(32))
    color_acento: Mapped[str | None] = mapped_column(String(32))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

    institucion: Mapped[Institucion] = relationship("Institucion", back_populates="complejos")
