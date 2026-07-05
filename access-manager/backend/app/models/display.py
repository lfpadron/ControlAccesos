from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PantallaTurnos(TimestampMixin, Base):
    __tablename__ = "pantallas_turnos"
    __table_args__ = (
        CheckConstraint("polling_interval_seconds BETWEEN 2 AND 10", name="polling_interval_range"),
        CheckConstraint("segundos_resaltado BETWEEN 5 AND 120", name="segundos_resaltado_range"),
        CheckConstraint("segundos_visible BETWEEN 30 AND 3600", name="segundos_visible_range"),
        CheckConstraint("max_turnos_visibles BETWEEN 1 AND 50", name="max_turnos_visibles_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo_dispositivo: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    token_hash: Mapped[str | None] = mapped_column(String(255))
    complejo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("complejos.id"), nullable=False, index=True)
    piso_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("pisos.id"), index=True)
    cluster_espera_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    consultorio_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("consultorios.id"), index=True)
    nombre: Mapped[str | None] = mapped_column(String(180))
    descripcion: Mapped[str | None] = mapped_column(Text)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    ultima_conexion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    polling_interval_seconds: Mapped[int] = mapped_column(Integer, default=5, server_default="5", nullable=False)
    color_fondo: Mapped[str | None] = mapped_column(String(40))
    color_texto: Mapped[str | None] = mapped_column(String(40))
    color_turno_nuevo: Mapped[str | None] = mapped_column(String(40))
    color_turno_normal: Mapped[str | None] = mapped_column(String(40))
    font_size_turno_nuevo: Mapped[int | None] = mapped_column(Integer)
    font_size_turno_normal: Mapped[int | None] = mapped_column(Integer)
    segundos_resaltado: Mapped[int] = mapped_column(Integer, default=25, server_default="25", nullable=False)
    segundos_visible: Mapped[int] = mapped_column(Integer, default=300, server_default="300", nullable=False)
    max_turnos_visibles: Mapped[int] = mapped_column(Integer, default=10, server_default="10", nullable=False)


class PantallaTurnosCluster(Base):
    __tablename__ = "pantallas_turnos_clusters"

    pantalla_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pantallas_turnos.id", ondelete="CASCADE"),
        primary_key=True,
    )
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clusters_turnos.id", ondelete="CASCADE"),
        primary_key=True,
    )


class TurnoDisplay(TimestampMixin, Base):
    __tablename__ = "turnos_display"
    __table_args__ = (
        CheckConstraint("estado IN ('NUEVO', 'VISIBLE', 'OCULTO', 'CANCELADO')", name="estado_valido"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cita_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("citas.id"), index=True)
    pantalla_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("pantallas_turnos.id"), index=True)
    complejo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("complejos.id"), nullable=False, index=True)
    piso_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("pisos.id"), index=True)
    cluster_espera_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    consultorio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("consultorios.id"), nullable=False, index=True)
    turno: Mapped[str] = mapped_column(String(40), nullable=False)
    consultorio: Mapped[str] = mapped_column(String(180), nullable=False)
    texto_visible: Mapped[str | None] = mapped_column(String(255))
    llamado_numero: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="NUEVO", server_default="NUEVO", nullable=False)
    llamado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resaltado_hasta: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    visible_hasta: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ocultado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    llamado_por: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), index=True)
