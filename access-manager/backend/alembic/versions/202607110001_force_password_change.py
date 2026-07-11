"""force password change flag

Revision ID: 202607110001
Revises: 202607050002
Create Date: 2026-07-11 00:01:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "202607110001"
down_revision = "202607050002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column(
            "force_password_change",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("usuarios", "force_password_change")
