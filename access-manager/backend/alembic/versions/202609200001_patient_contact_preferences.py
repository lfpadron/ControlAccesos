"""Agregar teléfonos y preferencias de contacto de pacientes.

Revision ID: 202609200001
Revises: 202608300003
Create Date: 2026-09-20 00:01:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202609200001"
down_revision = "202608300003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pacientes", sa.Column("telefono_1", sa.String(length=40), nullable=True))
    op.add_column(
        "pacientes",
        sa.Column("tipo_telefono_1", sa.String(length=12), nullable=False, server_default="FIJO"),
    )
    op.add_column(
        "pacientes",
        sa.Column("tipo_telefono_2", sa.String(length=12), nullable=False, server_default="CELULAR"),
    )
    op.add_column("pacientes", sa.Column("correo_electronico", sa.String(length=320), nullable=True))
    op.add_column("pacientes", sa.Column("metodo_confirmacion", sa.String(length=40), nullable=True))
    op.create_index("ix_pacientes_telefono_1", "pacientes", ["telefono_1"])
    op.create_check_constraint(
        "ck_pacientes_tipo_telefono_1",
        "pacientes",
        "tipo_telefono_1 IN ('FIJO', 'CELULAR')",
    )
    op.create_check_constraint(
        "ck_pacientes_tipo_telefono_2",
        "pacientes",
        "tipo_telefono_2 IN ('FIJO', 'CELULAR')",
    )
    op.create_check_constraint(
        "ck_pacientes_metodo_confirmacion",
        "pacientes",
        "metodo_confirmacion IS NULL OR metodo_confirmacion IN ("
        "'LLAMAR_FIJO_1', 'LLAMAR_FIJO_2', 'LLAMAR_CELULAR_1', 'LLAMAR_CELULAR_2', "
        "'WHATSAPP_1', 'WHATSAPP_2', 'TELEGRAM_1', 'TELEGRAM_2', 'CORREO')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_pacientes_metodo_confirmacion", "pacientes", type_="check")
    op.drop_constraint("ck_pacientes_tipo_telefono_2", "pacientes", type_="check")
    op.drop_constraint("ck_pacientes_tipo_telefono_1", "pacientes", type_="check")
    op.drop_index("ix_pacientes_telefono_1", table_name="pacientes")
    op.drop_column("pacientes", "metodo_confirmacion")
    op.drop_column("pacientes", "correo_electronico")
    op.drop_column("pacientes", "tipo_telefono_2")
    op.drop_column("pacientes", "tipo_telefono_1")
    op.drop_column("pacientes", "telefono_1")
