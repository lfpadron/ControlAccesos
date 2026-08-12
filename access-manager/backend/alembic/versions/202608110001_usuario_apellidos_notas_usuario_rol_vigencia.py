"""Usuario apellidos, notas y vigencia de asignaciones.

Revision ID: 202608110001
Revises: 202608070001
Create Date: 2026-08-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "202608110001"
down_revision = "202608070001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("apellidos", sa.String(length=180), nullable=True))
    op.add_column("usuarios", sa.Column("notas", sa.String(length=500), nullable=True))
    op.execute("UPDATE usuarios SET apellidos = 'Sin apellido' WHERE apellidos IS NULL OR trim(apellidos) = ''")
    op.alter_column("usuarios", "apellidos", existing_type=sa.String(length=180), nullable=False)

    op.add_column("usuario_roles", sa.Column("fecha_inicio", sa.Date(), nullable=True, server_default=sa.text("CURRENT_DATE")))
    op.add_column("usuario_roles", sa.Column("fecha_fin", sa.Date(), nullable=True))
    op.execute("UPDATE usuario_roles SET fecha_inicio = CURRENT_DATE WHERE fecha_inicio IS NULL")
    op.alter_column("usuario_roles", "fecha_inicio", existing_type=sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE"))


def downgrade() -> None:
    op.drop_column("usuario_roles", "fecha_fin")
    op.drop_column("usuario_roles", "fecha_inicio")
    op.drop_column("usuarios", "notas")
    op.drop_column("usuarios", "apellidos")
