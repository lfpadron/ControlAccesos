"""allow confidential patient preferred name

Revision ID: 202607050001
Revises: 202606120001
Create Date: 2026-07-05 00:01:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "202607050001"
down_revision = "202606120001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("pacientes", "nombre", existing_type=sa.String(length=180), nullable=True)
    op.alter_column("pacientes", "apellido_paterno", existing_type=sa.String(length=180), nullable=True)
    op.create_check_constraint(
        "ck_pacientes_identidad_minima",
        "pacientes",
        "nombre_preferido IS NOT NULL OR (nombre IS NOT NULL AND apellido_paterno IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_pacientes_identidad_minima", "pacientes", type_="check")
    op.execute("UPDATE pacientes SET nombre = COALESCE(nombre, nombre_preferido, 'Paciente') WHERE nombre IS NULL")
    op.execute("UPDATE pacientes SET apellido_paterno = COALESCE(apellido_paterno, 'Confidencial') WHERE apellido_paterno IS NULL")
    op.alter_column("pacientes", "apellido_paterno", existing_type=sa.String(length=180), nullable=False)
    op.alter_column("pacientes", "nombre", existing_type=sa.String(length=180), nullable=False)
