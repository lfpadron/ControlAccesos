"""Agregar pantalla inicial a roles.

Revision ID: 202608240002
Revises: 202608240001
Create Date: 2026-08-24 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202608240002"
down_revision = "202608240001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "roles",
        sa.Column("pantalla_inicial", sa.String(length=80), nullable=False, server_default="perfil"),
    )


def downgrade() -> None:
    op.drop_column("roles", "pantalla_inicial")
