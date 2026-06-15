from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PuntoAcceso(TimestampMixin, Base):
    __tablename__ = "puntos_acceso"
    __table_args__ = (UniqueConstraint("piso_id", "nombre", name="uq_puntos_acceso_piso_nombre"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complejo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("complejos.id"), nullable=False, index=True)
    piso_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pisos.id"), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(180), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)


class Kiosko(TimestampMixin, Base):
    __tablename__ = "kioskos"
    __table_args__ = (
        CheckConstraint("polling_interval_seconds BETWEEN 2 AND 30", name="kioskos_polling_interval_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo_dispositivo: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    complejo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("complejos.id"), nullable=False, index=True)
    piso_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pisos.id"), nullable=False, index=True)
    punto_acceso_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("puntos_acceso.id"), nullable=False, index=True)
    nombre: Mapped[str | None] = mapped_column(String(180))
    descripcion: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    ultima_conexion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    polling_interval_seconds: Mapped[int] = mapped_column(Integer, default=5, server_default="5", nullable=False)
    color_fondo: Mapped[str | None] = mapped_column(String(40))
    color_texto: Mapped[str | None] = mapped_column(String(40))
    color_primario: Mapped[str | None] = mapped_column(String(40))
    color_acento: Mapped[str | None] = mapped_column(String(40))
