"""Agregar estado No mostrar a medicos.

Revision ID: 202608300001
Revises: 202608280002
Create Date: 2026-08-30 00:01:00.000000
"""

from __future__ import annotations

from alembic import op


revision = "202608300001"
down_revision = "202608280002"
branch_labels = None
depends_on = None


ESTADOS_CON_NO_MOSTRAR = "'AUSENTE', 'NO_DISPONIBLE', 'EN_CONSULTA', 'DISPONIBLE', 'NO_MOSTRAR'"
ESTADOS_PREVIOS = "'AUSENTE', 'NO_DISPONIBLE', 'EN_CONSULTA', 'DISPONIBLE'"


def upgrade() -> None:
    op.drop_constraint("ck_medicos_estado_atencion", "medicos", type_="check")
    op.create_check_constraint(
        "ck_medicos_estado_atencion",
        "medicos",
        f"estado_atencion IN ({ESTADOS_CON_NO_MOSTRAR})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_medicos_estado_atencion", "medicos", type_="check")
    op.execute("UPDATE medicos SET estado_atencion = 'DISPONIBLE' WHERE estado_atencion = 'NO_MOSTRAR'")
    op.create_check_constraint(
        "ck_medicos_estado_atencion",
        "medicos",
        f"estado_atencion IN ({ESTADOS_PREVIOS})",
    )
