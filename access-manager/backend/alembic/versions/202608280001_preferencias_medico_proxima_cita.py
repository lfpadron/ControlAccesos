"""Agregar preferencias de medico y modo proxima cita.

Revision ID: 202608280001
Revises: 202608270001
Create Date: 2026-08-28 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202608280001"
down_revision = "202608270001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "medicos",
        sa.Column("duracion_cita_minutos", sa.Integer(), nullable=False, server_default="60"),
    )
    op.add_column("medicos", sa.Column("proxima_cita_estimada_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        "ck_medicos_duracion_cita_minutos_range",
        "medicos",
        "duracion_cita_minutos BETWEEN 15 AND 120",
    )
    op.add_column(
        "clusters_turnos",
        sa.Column("muestra_turnos", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "clusters_turnos",
        sa.Column("muestra_proxima_cita", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_check_constraint(
        "ck_clusters_turnos_modo_display",
        "clusters_turnos",
        "muestra_turnos OR muestra_proxima_cita",
    )


def downgrade() -> None:
    op.drop_constraint("ck_clusters_turnos_modo_display", "clusters_turnos", type_="check")
    op.drop_column("clusters_turnos", "muestra_proxima_cita")
    op.drop_column("clusters_turnos", "muestra_turnos")
    op.drop_constraint("ck_medicos_duracion_cita_minutos_range", "medicos", type_="check")
    op.drop_column("medicos", "proxima_cita_estimada_at")
    op.drop_column("medicos", "duracion_cita_minutos")
