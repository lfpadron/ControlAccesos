"""initial schema

Revision ID: 202606080001
Revises:
Create Date: 2026-06-08 00:01:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202606080001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "instituciones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("nombre", sa.String(length=180), nullable=False),
        sa.Column("razon_social", sa.String(length=255), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("color_primario", sa.String(length=32), nullable=True),
        sa.Column("color_secundario", sa.String(length=32), nullable=True),
        sa.Column("color_acento", sa.String(length=32), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "usuarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("nombre", sa.String(length=180), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=500), nullable=False),
        sa.Column("telefono", sa.String(length=64), nullable=True),
        sa.Column("two_factor_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("estado", sa.String(length=32), nullable=False, server_default=sa.text("'ACTIVO'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("email", name="uq_usuarios_email"),
    )

    op.create_table(
        "complejos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("institucion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=180), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("direccion", sa.Text(), nullable=True),
        sa.Column("telefono", sa.String(length=64), nullable=True),
        sa.Column("zona_horaria", sa.String(length=64), nullable=False),
        sa.Column("color_primario", sa.String(length=32), nullable=True),
        sa.Column("color_secundario", sa.String(length=32), nullable=True),
        sa.Column("color_acento", sa.String(length=32), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["institucion_id"], ["instituciones.id"], name="fk_complejos_institucion_id"),
    )

    op.create_table(
        "auditoria",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("evento", sa.String(length=120), nullable=False),
        sa.Column("entidad", sa.String(length=120), nullable=False),
        sa.Column("entidad_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("canal", sa.String(length=64), nullable=True),
        sa.Column("ip_origen", sa.String(length=64), nullable=True),
        sa.Column("valor_antes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("valor_despues", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], name="fk_auditoria_usuario_id"),
    )

    op.create_index("ix_complejos_institucion_id", "complejos", ["institucion_id"])
    op.create_index("ix_auditoria_entidad", "auditoria", ["entidad", "entidad_id"])
    op.create_index("ix_auditoria_created_at", "auditoria", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_auditoria_created_at", table_name="auditoria")
    op.drop_index("ix_auditoria_entidad", table_name="auditoria")
    op.drop_index("ix_complejos_institucion_id", table_name="complejos")
    op.drop_table("auditoria")
    op.drop_table("complejos")
    op.drop_table("usuarios")
    op.drop_table("instituciones")
