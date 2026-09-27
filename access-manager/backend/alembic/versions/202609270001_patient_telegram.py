"""Vincular los dos celulares de pacientes con Telegram.

Revision ID: 202609270001
Revises: 202609200001
"""

from alembic import op
import sqlalchemy as sa

revision = "202609270001"
down_revision = "202609200001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pacientes", sa.Column("telegram_chat_id_1", sa.BigInteger(), nullable=True))
    op.add_column("pacientes", sa.Column("telegram_chat_id_2", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("pacientes", "telegram_chat_id_2")
    op.drop_column("pacientes", "telegram_chat_id_1")
