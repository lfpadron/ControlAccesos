"""patient preferred name and kiosks

Revision ID: 202606120001
Revises: 202606100002
Create Date: 2026-06-12 00:01:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202606120001"
down_revision = "202606100002"
branch_labels = None
depends_on = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    ]


def upgrade() -> None:
    op.add_column("pacientes", sa.Column("nombre_preferido", sa.String(length=60), nullable=True))

    op.create_table(
        "puntos_acceso",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("complejo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("piso_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=180), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *timestamps(),
        sa.ForeignKeyConstraint(["complejo_id"], ["complejos.id"], name="fk_puntos_acceso_complejo_id"),
        sa.ForeignKeyConstraint(["piso_id"], ["pisos.id"], name="fk_puntos_acceso_piso_id"),
        sa.UniqueConstraint("piso_id", "nombre", name="uq_puntos_acceso_piso_nombre"),
    )
    op.create_index("ix_puntos_acceso_complejo_id", "puntos_acceso", ["complejo_id"])
    op.create_index("ix_puntos_acceso_piso_id", "puntos_acceso", ["piso_id"])

    op.create_table(
        "kioskos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("codigo_dispositivo", sa.String(length=120), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("complejo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("piso_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("punto_acceso_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=180), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("ultima_conexion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("polling_interval_seconds", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("color_fondo", sa.String(length=40), nullable=True),
        sa.Column("color_texto", sa.String(length=40), nullable=True),
        sa.Column("color_primario", sa.String(length=40), nullable=True),
        sa.Column("color_acento", sa.String(length=40), nullable=True),
        *timestamps(),
        sa.CheckConstraint("polling_interval_seconds BETWEEN 2 AND 30", name="kioskos_polling_interval_range"),
        sa.ForeignKeyConstraint(["complejo_id"], ["complejos.id"], name="fk_kioskos_complejo_id"),
        sa.ForeignKeyConstraint(["piso_id"], ["pisos.id"], name="fk_kioskos_piso_id"),
        sa.ForeignKeyConstraint(["punto_acceso_id"], ["puntos_acceso.id"], name="fk_kioskos_punto_acceso_id"),
        sa.UniqueConstraint("codigo_dispositivo", name="uq_kioskos_codigo_dispositivo"),
    )
    op.create_index("ix_kioskos_codigo_dispositivo", "kioskos", ["codigo_dispositivo"])
    op.create_index("ix_kioskos_complejo_id", "kioskos", ["complejo_id"])
    op.create_index("ix_kioskos_piso_id", "kioskos", ["piso_id"])
    op.create_index("ix_kioskos_punto_acceso_id", "kioskos", ["punto_acceso_id"])


def downgrade() -> None:
    op.drop_index("ix_kioskos_punto_acceso_id", table_name="kioskos")
    op.drop_index("ix_kioskos_piso_id", table_name="kioskos")
    op.drop_index("ix_kioskos_complejo_id", table_name="kioskos")
    op.drop_index("ix_kioskos_codigo_dispositivo", table_name="kioskos")
    op.drop_table("kioskos")
    op.drop_index("ix_puntos_acceso_piso_id", table_name="puntos_acceso")
    op.drop_index("ix_puntos_acceso_complejo_id", table_name="puntos_acceso")
    op.drop_table("puntos_acceso")
    op.drop_column("pacientes", "nombre_preferido")
