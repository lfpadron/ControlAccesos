"""turn display templates and call limits

Revision ID: 202607050002
Revises: 202607050001
Create Date: 2026-07-05 00:02:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "202607050002"
down_revision = "202607050001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "medicos",
        sa.Column("plantilla_turno", sa.String(length=40), server_default="PACIENTE_CONSULTORIO", nullable=False),
    )
    op.create_check_constraint(
        "ck_medicos_plantilla_turno",
        "medicos",
        "plantilla_turno IN ('PACIENTE_CONSULTORIO', 'TURNO_PACIENTE_CONSULTORIO', "
        "'PACIENTE_TURNO_CONSULTORIO', 'TURNO_CONSULTORIO')",
    )
    op.add_column("turnos_display", sa.Column("texto_visible", sa.String(length=255), nullable=True))
    op.add_column("turnos_display", sa.Column("llamado_numero", sa.Integer(), server_default="1", nullable=False))


def downgrade() -> None:
    op.drop_column("turnos_display", "llamado_numero")
    op.drop_column("turnos_display", "texto_visible")
    op.drop_constraint("ck_medicos_plantilla_turno", "medicos", type_="check")
    op.drop_column("medicos", "plantilla_turno")
