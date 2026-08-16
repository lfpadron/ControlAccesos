"""Agregar notas a consultorios.

Revision ID: 202608160001
Revises: 202608130001
Create Date: 2026-08-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "202608160001"
down_revision = "202608130001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("consultorios", sa.Column("notas", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("consultorios", "notas")
