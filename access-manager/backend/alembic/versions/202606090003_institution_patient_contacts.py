"""institution patient contacts updates

Revision ID: 202606090003
Revises: 202606090002
Create Date: 2026-06-09 00:03:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202606090003"
down_revision = "202606090002"
branch_labels = None
depends_on = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    ]


def upgrade() -> None:
    op.add_column("instituciones", sa.Column("notas", sa.String(length=500), nullable=True))
    op.execute("UPDATE instituciones SET nombre = left(nombre, 120)")
    op.execute("UPDATE instituciones SET razon_social = left(razon_social, 120) WHERE razon_social IS NOT NULL")
    op.alter_column("instituciones", "nombre", existing_type=sa.String(length=180), type_=sa.String(length=120), nullable=False)
    op.alter_column("instituciones", "razon_social", existing_type=sa.String(length=255), type_=sa.String(length=120), nullable=True)

    op.add_column("pacientes", sa.Column("desactivado_en", sa.DateTime(timezone=True), nullable=True))
    op.add_column("pacientes", sa.Column("marcado_borrado_en", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "contactos_institucionales",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("nombre", sa.String(length=180), nullable=False),
        sa.Column("medios_contacto", postgresql.JSONB(), nullable=False),
        sa.Column("tipo_contacto", sa.String(length=32), nullable=False),
        sa.Column("notas", sa.Text(), nullable=True),
        *timestamps(),
        sa.CheckConstraint(
            "tipo_contacto IN ('PRIMARIO', 'SECUNDARIO', 'SOLO_EMERGENCIAS')",
            name="ck_contactos_institucionales_tipo_contacto_valido",
        ),
    )
    op.create_table(
        "contactos_institucionales_complejos",
        sa.Column("contacto_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("complejo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["contacto_id"],
            ["contactos_institucionales.id"],
            name="fk_contacto_complejo_contacto",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["complejo_id"],
            ["complejos.id"],
            name="fk_contacto_complejo_complejo",
        ),
        sa.PrimaryKeyConstraint("contacto_id", "complejo_id", name="pk_contactos_institucionales_complejos"),
    )


def downgrade() -> None:
    op.drop_table("contactos_institucionales_complejos")
    op.drop_table("contactos_institucionales")
    op.drop_column("pacientes", "marcado_borrado_en")
    op.drop_column("pacientes", "desactivado_en")
    op.alter_column("instituciones", "razon_social", existing_type=sa.String(length=120), type_=sa.String(length=255), nullable=True)
    op.alter_column("instituciones", "nombre", existing_type=sa.String(length=120), type_=sa.String(length=180), nullable=False)
    op.drop_column("instituciones", "notas")
