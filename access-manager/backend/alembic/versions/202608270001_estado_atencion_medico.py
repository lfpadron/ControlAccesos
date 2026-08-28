"""Agregar estado de atencion a medicos.

Revision ID: 202608270001
Revises: 202608240002
Create Date: 2026-08-27 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202608270001"
down_revision = "202608240002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "medicos",
        sa.Column("estado_atencion", sa.String(length=32), nullable=False, server_default="DISPONIBLE"),
    )
    op.add_column("medicos", sa.Column("notas_estado", sa.String(length=100), nullable=True))
    op.create_check_constraint(
        "ck_medicos_estado_atencion",
        "medicos",
        "estado_atencion IN ('AUSENTE', 'NO_DISPONIBLE', 'EN_CONSULTA', 'DISPONIBLE')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_medicos_estado_atencion", "medicos", type_="check")
    op.drop_column("medicos", "notas_estado")
    op.drop_column("medicos", "estado_atencion")
