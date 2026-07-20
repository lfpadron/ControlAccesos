"""set demo patient birthdate

Revision ID: 202607190001
Revises: 202607110001
Create Date: 2026-07-19 00:01:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "202607190001"
down_revision = "202607110001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE pacientes
        SET fecha_nacimiento = DATE '1970-01-01'
        WHERE folio_paciente = 'PDEMO246'
          AND fecha_nacimiento IS NULL
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE pacientes
        SET fecha_nacimiento = NULL
        WHERE folio_paciente = 'PDEMO246'
          AND fecha_nacimiento = DATE '1970-01-01'
        """
    )
