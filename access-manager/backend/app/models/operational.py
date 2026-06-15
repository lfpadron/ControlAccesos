from __future__ import annotations

from datetime import date, time
import uuid

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Integer, String, Text, Time, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Role(TimestampMixin, Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(180), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)


class UsuarioRol(TimestampMixin, Base):
    __tablename__ = "usuario_roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False, index=True)
    rol_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False, index=True)
    institucion_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("instituciones.id"), index=True)
    complejo_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("complejos.id"), index=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)


class Piso(TimestampMixin, Base):
    __tablename__ = "pisos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complejo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("complejos.id"), nullable=False, index=True)
    numero: Mapped[str] = mapped_column(String(40), nullable=False)
    nombre_visible: Mapped[str] = mapped_column(String(180), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)


class SalaEspera(TimestampMixin, Base):
    __tablename__ = "salas_espera"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complejo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("complejos.id"), nullable=False, index=True)
    piso_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pisos.id"), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(180), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    capacidad_estimada: Mapped[int | None] = mapped_column(Integer)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)


class Consultorio(TimestampMixin, Base):
    __tablename__ = "consultorios"
    __table_args__ = (UniqueConstraint("complejo_id", "codigo", name="uq_consultorios_complejo_codigo"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complejo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("complejos.id"), nullable=False, index=True)
    piso_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pisos.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(80), nullable=False)
    nombre_visible: Mapped[str | None] = mapped_column(String(180))
    instrucciones_acceso: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)


class ClusterTurnos(TimestampMixin, Base):
    __tablename__ = "clusters_turnos"
    __table_args__ = (UniqueConstraint("piso_id", "nombre", name="uq_clusters_turnos_piso_nombre"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complejo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("complejos.id"), nullable=False, index=True)
    piso_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pisos.id"), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(180), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)


class ConsultorioCluster(Base):
    __tablename__ = "consultorios_clusters"

    consultorio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("consultorios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clusters_turnos.id", ondelete="CASCADE"),
        primary_key=True,
    )


class Medico(TimestampMixin, Base):
    __tablename__ = "medicos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(180), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(180), nullable=False)
    nombre_visible: Mapped[str | None] = mapped_column(String(220))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)


class Operador(TimestampMixin, Base):
    __tablename__ = "operadores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False, index=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)


class AsignacionMedicoConsultorio(TimestampMixin, Base):
    __tablename__ = "asignaciones_medico_consultorio"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medico_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("medicos.id"), nullable=False, index=True)
    consultorio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("consultorios.id"), nullable=False, index=True)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date | None] = mapped_column(Date)
    hora_inicio: Mapped[time | None] = mapped_column(Time)
    hora_fin: Mapped[time | None] = mapped_column(Time)
    dias_semana: Mapped[str | None] = mapped_column(String(120))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)


class AsignacionOperador(TimestampMixin, Base):
    __tablename__ = "asignaciones_operador"
    __table_args__ = (
        CheckConstraint("medico_id IS NOT NULL OR consultorio_id IS NOT NULL", name="ck_asignaciones_operador_destino"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operador_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("operadores.id"), nullable=False, index=True)
    medico_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("medicos.id"), index=True)
    consultorio_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("consultorios.id"), index=True)
    complejo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("complejos.id"), nullable=False, index=True)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date | None] = mapped_column(Date)
    prioridad: Mapped[int] = mapped_column(Integer, default=100, server_default="100", nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
