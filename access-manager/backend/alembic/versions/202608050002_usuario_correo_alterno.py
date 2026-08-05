"""usuario correo alterno

Revision ID: 202608050002
Revises: 202608050001
Create Date: 2026-08-05 00:02:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "202608050002"
down_revision = "202608050001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("correo_alterno", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("usuarios", "correo_alterno")
