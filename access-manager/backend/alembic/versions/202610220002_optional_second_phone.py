"""Permitir pacientes con solo telefono 1 y sin fecha de nacimiento.

Revision ID: 202610220002
Revises: 202610220001
"""

from alembic import op

revision = "202610220002"
down_revision = "202610220001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_pacientes_contacto_o_fecha_nacimiento", "pacientes", type_="check")
    op.create_check_constraint(
        "ck_pacientes_contacto_o_fecha_nacimiento",
        "pacientes",
        "telefono_1 IS NOT NULL OR celular IS NOT NULL OR fecha_nacimiento IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_pacientes_contacto_o_fecha_nacimiento", "pacientes", type_="check")
    op.create_check_constraint(
        "ck_pacientes_contacto_o_fecha_nacimiento",
        "pacientes",
        "celular IS NOT NULL OR fecha_nacimiento IS NOT NULL",
    )
