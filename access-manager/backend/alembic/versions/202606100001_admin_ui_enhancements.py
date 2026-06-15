"""admin ui enhancements

Revision ID: 202606100001
Revises: 202606090003
Create Date: 2026-06-10 00:01:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "202606100001"
down_revision = "202606090003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pantallas_turnos", sa.Column("descripcion", sa.Text(), nullable=True))
    op.drop_constraint("ck_contactos_institucionales_tipo_contacto_valido", "contactos_institucionales", type_="check")
    op.add_column("contactos_institucionales", sa.Column("tipo_contacto_descripcion", sa.String(length=50), nullable=True))
    op.create_check_constraint(
        "ck_contactos_institucionales_tipo_contacto_valido",
        "contactos_institucionales",
        "tipo_contacto IN ('PRIMARIO', 'SECUNDARIO', 'SOLO_EMERGENCIAS', 'OTRO')",
    )


def downgrade() -> None:
    op.execute("UPDATE contactos_institucionales SET tipo_contacto = 'SECUNDARIO' WHERE tipo_contacto = 'OTRO'")
    op.drop_constraint("ck_contactos_institucionales_tipo_contacto_valido", "contactos_institucionales", type_="check")
    op.drop_column("contactos_institucionales", "tipo_contacto_descripcion")
    op.create_check_constraint(
        "ck_contactos_institucionales_tipo_contacto_valido",
        "contactos_institucionales",
        "tipo_contacto IN ('PRIMARIO', 'SECUNDARIO', 'SOLO_EMERGENCIAS')",
    )
    op.drop_column("pantallas_turnos", "descripcion")
