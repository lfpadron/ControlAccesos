from __future__ import annotations

from datetime import date, datetime, time
import uuid

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, Time, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Paciente(TimestampMixin, Base):
    __tablename__ = "pacientes"
    __table_args__ = (
        CheckConstraint("celular IS NOT NULL OR fecha_nacimiento IS NOT NULL", name="contacto_o_fecha_nacimiento"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    folio_paciente: Mapped[str] = mapped_column(String(24), unique=True, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(180), nullable=False)
    nombre_preferido: Mapped[str | None] = mapped_column(String(60))
    apellido_paterno: Mapped[str] = mapped_column(String(180), nullable=False)
    apellido_materno: Mapped[str | None] = mapped_column(String(180))
    celular: Mapped[str | None] = mapped_column(String(40), index=True)
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    desactivado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    marcado_borrado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Cita(TimestampMixin, Base):
    __tablename__ = "citas"
    __table_args__ = (
        UniqueConstraint("complejo_id", "fecha_cita", "folio_turno", name="uq_citas_complejo_fecha_folio"),
        CheckConstraint("tipo IN ('PROGRAMADA', 'ESPONTANEA')", name="tipo_valido"),
        CheckConstraint(
            "estado IN ('AGENDADA', 'QR_GENERADO', 'LLEGO_LOBBY', 'AUTORIZADO_PASAR', "
            "'EN_CONSULTA', 'FINALIZADA', 'NO_LLEGO', 'CANCELADA', 'EXPIRADA')",
            name="estado_valido",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo: Mapped[str] = mapped_column(String(24), nullable=False)
    estado: Mapped[str] = mapped_column(String(40), default="AGENDADA", server_default="AGENDADA", nullable=False)
    paciente_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pacientes.id"), nullable=False, index=True)
    medico_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("medicos.id"), nullable=False, index=True)
    consultorio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("consultorios.id"), nullable=False, index=True)
    complejo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("complejos.id"), nullable=False, index=True)
    piso_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pisos.id"), nullable=False, index=True)
    sala_prevista_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("salas_espera.id"), index=True)
    cluster_espera_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    fecha_cita: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    hora_cita: Mapped[time] = mapped_column(Time, nullable=False)
    duracion_estimada: Mapped[int | None] = mapped_column(Integer)
    folio_turno: Mapped[str] = mapped_column(String(4), nullable=False)
    origen: Mapped[str | None] = mapped_column(String(80))
    notas_operativas: Mapped[str | None] = mapped_column(Text)
    creada_por: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), index=True)


class QrToken(TimestampMixin, Base):
    __tablename__ = "qr_tokens"
    __table_args__ = (
        CheckConstraint("estado IN ('GENERADO', 'USADO', 'EXPIRADO', 'CANCELADO')", name="estado_valido"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cita_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("citas.id"), nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String(24), default="GENERADO", server_default="GENERADO", nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    fecha_emision: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_expiracion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EventoLlegada(Base):
    __tablename__ = "eventos_llegada"
    __table_args__ = (
        CheckConstraint("tipo IN ('CHECKIN_LOBBY', 'CHECKIN_SALA')", name="tipo_valido"),
        CheckConstraint(
            "canal IN ('KIOSKO', 'RECEPCION', 'OPERADOR', 'APP_MOVIL', 'BOT_TELEGRAM', 'API_EXTERNA')",
            name="canal_valido",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cita_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("citas.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    sala_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("salas_espera.id"), index=True)
    canal: Mapped[str] = mapped_column(String(32), nullable=False)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), index=True)
    dispositivo_id: Mapped[str | None] = mapped_column(String(120))
    ip_origen: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
