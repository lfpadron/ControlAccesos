"""Agregar prefijo de usuario y permitir tipo de telefono 2 sin seleccionar.

Revision ID: 202610220001
Revises: 202609270001
"""

from alembic import op
import sqlalchemy as sa

revision = "202610220001"
down_revision = "202609270001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("prefijo", sa.String(length=64), nullable=True))
    op.alter_column("pacientes", "tipo_telefono_2", existing_type=sa.String(length=12), nullable=True)


def downgrade() -> None:
    op.execute("UPDATE pacientes SET tipo_telefono_2 = 'CELULAR' WHERE tipo_telefono_2 IS NULL")
    op.alter_column("pacientes", "tipo_telefono_2", existing_type=sa.String(length=12), nullable=False)
    op.drop_column("usuarios", "prefijo")
