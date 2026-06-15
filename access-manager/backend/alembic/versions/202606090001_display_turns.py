"""display turns

Revision ID: 202606090001
Revises: 202606080002
Create Date: 2026-06-09 00:01:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202606090001"
down_revision = "202606080002"
branch_labels = None
depends_on = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    ]


def upgrade() -> None:
    op.create_table(
        "citas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("complejo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("piso_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cluster_espera_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("consultorio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turno", sa.String(length=40), nullable=False),
        sa.Column("estado", sa.String(length=40), nullable=False, server_default="PROGRAMADA"),
        *timestamps(),
        sa.ForeignKeyConstraint(["complejo_id"], ["complejos.id"], name="fk_citas_complejo_id"),
        sa.ForeignKeyConstraint(["piso_id"], ["pisos.id"], name="fk_citas_piso_id"),
        sa.ForeignKeyConstraint(["consultorio_id"], ["consultorios.id"], name="fk_citas_consultorio_id"),
    )
    op.create_index("ix_citas_complejo_id", "citas", ["complejo_id"])
    op.create_index("ix_citas_piso_id", "citas", ["piso_id"])
    op.create_index("ix_citas_cluster_espera_id", "citas", ["cluster_espera_id"])
    op.create_index("ix_citas_consultorio_id", "citas", ["consultorio_id"])

    op.create_table(
        "pantallas_turnos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("codigo_dispositivo", sa.String(length=120), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=True),
        sa.Column("complejo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("piso_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cluster_espera_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("consultorio_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("nombre", sa.String(length=180), nullable=True),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("ultima_conexion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("polling_interval_seconds", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("color_fondo", sa.String(length=40), nullable=True),
        sa.Column("color_texto", sa.String(length=40), nullable=True),
        sa.Column("color_turno_nuevo", sa.String(length=40), nullable=True),
        sa.Column("color_turno_normal", sa.String(length=40), nullable=True),
        sa.Column("font_size_turno_nuevo", sa.Integer(), nullable=True),
        sa.Column("font_size_turno_normal", sa.Integer(), nullable=True),
        sa.Column("segundos_resaltado", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("segundos_visible", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("max_turnos_visibles", sa.Integer(), nullable=False, server_default="10"),
        *timestamps(),
        sa.CheckConstraint("polling_interval_seconds BETWEEN 2 AND 10", name="ck_pantallas_turnos_polling_interval_range"),
        sa.CheckConstraint("segundos_resaltado BETWEEN 5 AND 120", name="ck_pantallas_turnos_segundos_resaltado_range"),
        sa.CheckConstraint("segundos_visible BETWEEN 30 AND 3600", name="ck_pantallas_turnos_segundos_visible_range"),
        sa.CheckConstraint("max_turnos_visibles BETWEEN 1 AND 50", name="ck_pantallas_turnos_max_turnos_visibles_range"),
        sa.ForeignKeyConstraint(["complejo_id"], ["complejos.id"], name="fk_pantallas_turnos_complejo_id"),
        sa.ForeignKeyConstraint(["piso_id"], ["pisos.id"], name="fk_pantallas_turnos_piso_id"),
        sa.ForeignKeyConstraint(["consultorio_id"], ["consultorios.id"], name="fk_pantallas_turnos_consultorio_id"),
        sa.UniqueConstraint("codigo_dispositivo", name="uq_pantallas_turnos_codigo_dispositivo"),
    )
    op.create_index("ix_pantallas_turnos_codigo_dispositivo", "pantallas_turnos", ["codigo_dispositivo"])
    op.create_index("ix_pantallas_turnos_complejo_id", "pantallas_turnos", ["complejo_id"])
    op.create_index("ix_pantallas_turnos_piso_id", "pantallas_turnos", ["piso_id"])
    op.create_index("ix_pantallas_turnos_cluster_espera_id", "pantallas_turnos", ["cluster_espera_id"])
    op.create_index("ix_pantallas_turnos_consultorio_id", "pantallas_turnos", ["consultorio_id"])

    op.create_table(
        "turnos_display",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("cita_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("pantalla_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("complejo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("piso_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cluster_espera_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("consultorio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turno", sa.String(length=40), nullable=False),
        sa.Column("consultorio", sa.String(length=180), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="NUEVO"),
        sa.Column("llamado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resaltado_hasta", sa.DateTime(timezone=True), nullable=False),
        sa.Column("visible_hasta", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ocultado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("llamado_por", postgresql.UUID(as_uuid=True), nullable=True),
        *timestamps(),
        sa.CheckConstraint("estado IN ('NUEVO', 'VISIBLE', 'OCULTO', 'CANCELADO')", name="ck_turnos_display_estado_valido"),
        sa.ForeignKeyConstraint(["cita_id"], ["citas.id"], name="fk_turnos_display_cita_id"),
        sa.ForeignKeyConstraint(["pantalla_id"], ["pantallas_turnos.id"], name="fk_turnos_display_pantalla_id"),
        sa.ForeignKeyConstraint(["complejo_id"], ["complejos.id"], name="fk_turnos_display_complejo_id"),
        sa.ForeignKeyConstraint(["piso_id"], ["pisos.id"], name="fk_turnos_display_piso_id"),
        sa.ForeignKeyConstraint(["consultorio_id"], ["consultorios.id"], name="fk_turnos_display_consultorio_id"),
        sa.ForeignKeyConstraint(["llamado_por"], ["usuarios.id"], name="fk_turnos_display_llamado_por"),
    )
    op.create_index("ix_turnos_display_cita_id", "turnos_display", ["cita_id"])
    op.create_index("ix_turnos_display_pantalla_id", "turnos_display", ["pantalla_id"])
    op.create_index("ix_turnos_display_complejo_id", "turnos_display", ["complejo_id"])
    op.create_index("ix_turnos_display_piso_id", "turnos_display", ["piso_id"])
    op.create_index("ix_turnos_display_cluster_espera_id", "turnos_display", ["cluster_espera_id"])
    op.create_index("ix_turnos_display_consultorio_id", "turnos_display", ["consultorio_id"])
    op.create_index("ix_turnos_display_llamado_en", "turnos_display", ["llamado_en"])
    op.create_index("ix_turnos_display_llamado_por", "turnos_display", ["llamado_por"])


def downgrade() -> None:
    op.drop_table("turnos_display")
    op.drop_table("pantallas_turnos")
    op.drop_table("citas")
