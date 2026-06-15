"""operational layer

Revision ID: 202606080002
Revises: 202606080001
Create Date: 2026-06-08 00:02:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202606080002"
down_revision = "202606080001"
branch_labels = None
depends_on = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    ]


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("codigo", sa.String(length=80), nullable=False),
        sa.Column("nombre", sa.String(length=180), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *timestamps(),
        sa.UniqueConstraint("codigo", name="uq_roles_codigo"),
    )
    op.create_index("ix_roles_codigo", "roles", ["codigo"])

    op.create_table(
        "usuario_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("institucion_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("complejo_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *timestamps(),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], name="fk_usuario_roles_usuario_id"),
        sa.ForeignKeyConstraint(["rol_id"], ["roles.id"], name="fk_usuario_roles_rol_id"),
        sa.ForeignKeyConstraint(["institucion_id"], ["instituciones.id"], name="fk_usuario_roles_institucion_id"),
        sa.ForeignKeyConstraint(["complejo_id"], ["complejos.id"], name="fk_usuario_roles_complejo_id"),
    )
    op.create_index("ix_usuario_roles_usuario_id", "usuario_roles", ["usuario_id"])
    op.create_index("ix_usuario_roles_rol_id", "usuario_roles", ["rol_id"])
    op.create_index("ix_usuario_roles_institucion_id", "usuario_roles", ["institucion_id"])
    op.create_index("ix_usuario_roles_complejo_id", "usuario_roles", ["complejo_id"])

    op.create_table(
        "pisos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("complejo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("numero", sa.String(length=40), nullable=False),
        sa.Column("nombre_visible", sa.String(length=180), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *timestamps(),
        sa.ForeignKeyConstraint(["complejo_id"], ["complejos.id"], name="fk_pisos_complejo_id"),
    )
    op.create_index("ix_pisos_complejo_id", "pisos", ["complejo_id"])

    op.create_table(
        "salas_espera",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("complejo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("piso_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=180), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("capacidad_estimada", sa.Integer(), nullable=True),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *timestamps(),
        sa.ForeignKeyConstraint(["complejo_id"], ["complejos.id"], name="fk_salas_espera_complejo_id"),
        sa.ForeignKeyConstraint(["piso_id"], ["pisos.id"], name="fk_salas_espera_piso_id"),
    )
    op.create_index("ix_salas_espera_complejo_id", "salas_espera", ["complejo_id"])
    op.create_index("ix_salas_espera_piso_id", "salas_espera", ["piso_id"])

    op.create_table(
        "consultorios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("complejo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("piso_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("codigo", sa.String(length=80), nullable=False),
        sa.Column("nombre_visible", sa.String(length=180), nullable=True),
        sa.Column("instrucciones_acceso", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *timestamps(),
        sa.ForeignKeyConstraint(["complejo_id"], ["complejos.id"], name="fk_consultorios_complejo_id"),
        sa.ForeignKeyConstraint(["piso_id"], ["pisos.id"], name="fk_consultorios_piso_id"),
        sa.UniqueConstraint("complejo_id", "codigo", name="uq_consultorios_complejo_codigo"),
    )
    op.create_index("ix_consultorios_complejo_id", "consultorios", ["complejo_id"])
    op.create_index("ix_consultorios_piso_id", "consultorios", ["piso_id"])

    op.create_table(
        "medicos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("nombre", sa.String(length=180), nullable=False),
        sa.Column("apellidos", sa.String(length=180), nullable=False),
        sa.Column("nombre_visible", sa.String(length=220), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *timestamps(),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], name="fk_medicos_usuario_id"),
    )
    op.create_index("ix_medicos_usuario_id", "medicos", ["usuario_id"])

    op.create_table(
        "operadores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *timestamps(),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], name="fk_operadores_usuario_id"),
    )
    op.create_index("ix_operadores_usuario_id", "operadores", ["usuario_id"])

    op.create_table(
        "asignaciones_medico_consultorio",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("medico_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consultorio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("fecha_fin", sa.Date(), nullable=True),
        sa.Column("hora_inicio", sa.Time(), nullable=True),
        sa.Column("hora_fin", sa.Time(), nullable=True),
        sa.Column("dias_semana", sa.String(length=120), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *timestamps(),
        sa.ForeignKeyConstraint(["medico_id"], ["medicos.id"], name="fk_asignaciones_medico_consultorio_medico_id"),
        sa.ForeignKeyConstraint(["consultorio_id"], ["consultorios.id"], name="fk_asignaciones_medico_consultorio_consultorio_id"),
    )
    op.create_index("ix_asignaciones_medico_consultorio_medico_id", "asignaciones_medico_consultorio", ["medico_id"])
    op.create_index("ix_asignaciones_medico_consultorio_consultorio_id", "asignaciones_medico_consultorio", ["consultorio_id"])

    op.create_table(
        "asignaciones_operador",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("operador_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("medico_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("consultorio_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("complejo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("fecha_fin", sa.Date(), nullable=True),
        sa.Column("prioridad", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *timestamps(),
        sa.CheckConstraint("medico_id IS NOT NULL OR consultorio_id IS NOT NULL", name="ck_asignaciones_operador_destino"),
        sa.ForeignKeyConstraint(["operador_id"], ["operadores.id"], name="fk_asignaciones_operador_operador_id"),
        sa.ForeignKeyConstraint(["medico_id"], ["medicos.id"], name="fk_asignaciones_operador_medico_id"),
        sa.ForeignKeyConstraint(["consultorio_id"], ["consultorios.id"], name="fk_asignaciones_operador_consultorio_id"),
        sa.ForeignKeyConstraint(["complejo_id"], ["complejos.id"], name="fk_asignaciones_operador_complejo_id"),
    )
    op.create_index("ix_asignaciones_operador_operador_id", "asignaciones_operador", ["operador_id"])
    op.create_index("ix_asignaciones_operador_medico_id", "asignaciones_operador", ["medico_id"])
    op.create_index("ix_asignaciones_operador_consultorio_id", "asignaciones_operador", ["consultorio_id"])
    op.create_index("ix_asignaciones_operador_complejo_id", "asignaciones_operador", ["complejo_id"])


def downgrade() -> None:
    op.drop_table("asignaciones_operador")
    op.drop_table("asignaciones_medico_consultorio")
    op.drop_table("operadores")
    op.drop_table("medicos")
    op.drop_table("consultorios")
    op.drop_table("salas_espera")
    op.drop_table("pisos")
    op.drop_table("usuario_roles")
    op.drop_index("ix_roles_codigo", table_name="roles")
    op.drop_table("roles")
