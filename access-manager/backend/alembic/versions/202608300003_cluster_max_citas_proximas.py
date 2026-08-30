"""Agregar maximo de citas proximas por cluster.

Revision ID: 202608300003
Revises: 202608300002
Create Date: 2026-08-30 00:03:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202608300003"
down_revision = "202608300002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "clusters_turnos",
        sa.Column("max_citas_proximas", sa.Integer(), nullable=False, server_default="10"),
    )
    op.create_check_constraint(
        "ck_clusters_turnos_max_citas_proximas_range",
        "clusters_turnos",
        "max_citas_proximas BETWEEN 5 AND 50",
    )


def downgrade() -> None:
    op.drop_constraint("ck_clusters_turnos_max_citas_proximas_range", "clusters_turnos", type_="check")
    op.drop_column("clusters_turnos", "max_citas_proximas")
