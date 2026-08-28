"""Ampliar rango de polling de pantallas de turnos.

Revision ID: 202608280002
Revises: 202608280001
Create Date: 2026-08-28 00:02:00.000000
"""

from __future__ import annotations

from alembic import op


revision = "202608280002"
down_revision = "202608280001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_pantallas_turnos_polling_interval_range", "pantallas_turnos", type_="check")
    op.execute("UPDATE pantallas_turnos SET polling_interval_seconds = 5 WHERE polling_interval_seconds < 5")
    op.execute("UPDATE pantallas_turnos SET polling_interval_seconds = 60 WHERE polling_interval_seconds > 60")
    op.create_check_constraint(
        "ck_pantallas_turnos_polling_interval_range",
        "pantallas_turnos",
        "polling_interval_seconds BETWEEN 5 AND 60",
    )


def downgrade() -> None:
    op.drop_constraint("ck_pantallas_turnos_polling_interval_range", "pantallas_turnos", type_="check")
    op.execute("UPDATE pantallas_turnos SET polling_interval_seconds = 10 WHERE polling_interval_seconds > 10")
    op.execute("UPDATE pantallas_turnos SET polling_interval_seconds = 2 WHERE polling_interval_seconds < 2")
    op.create_check_constraint(
        "ck_pantallas_turnos_polling_interval_range",
        "pantallas_turnos",
        "polling_interval_seconds BETWEEN 2 AND 10",
    )
