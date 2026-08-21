"""Asignar contactos institucionales a torres.

Revision ID: 202608210001
Revises: 202608160001
Create Date: 2026-08-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202608210001"
down_revision = "202608160001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contactos_institucionales_torres",
        sa.Column("contacto_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("torre_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["contacto_id"],
            ["contactos_institucionales.id"],
            name="fk_contacto_torre_contacto",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["torre_id"], ["torres.id"], name="fk_contacto_torre_torre"),
        sa.PrimaryKeyConstraint("contacto_id", "torre_id", name="pk_contactos_institucionales_torres"),
    )
    op.create_index("ix_contactos_institucionales_torres_torre_id", "contactos_institucionales_torres", ["torre_id"])


def downgrade() -> None:
    op.drop_index("ix_contactos_institucionales_torres_torre_id", table_name="contactos_institucionales_torres")
    op.drop_table("contactos_institucionales_torres")
