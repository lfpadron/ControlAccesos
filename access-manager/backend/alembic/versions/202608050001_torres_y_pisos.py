"""torres y pisos

Revision ID: 202608050001
Revises: 202607190001
Create Date: 2026-08-05 00:01:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202608050001"
down_revision = "202607190001"
branch_labels = None
depends_on = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    ]


def upgrade() -> None:
    op.create_table(
        "torres",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("complejo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=180), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("numero_pisos", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *timestamps(),
        sa.CheckConstraint("numero_pisos BETWEEN 1 AND 99", name="ck_torres_numero_pisos_range"),
        sa.ForeignKeyConstraint(["complejo_id"], ["complejos.id"], name="fk_torres_complejo_id"),
    )
    op.create_index("ix_torres_complejo_id", "torres", ["complejo_id"])

    op.add_column("pisos", sa.Column("torre_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_pisos_torre_id", "pisos", ["torre_id"])
    op.create_foreign_key("fk_pisos_torre_id_torres", "pisos", "torres", ["torre_id"], ["id"])

    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute(
        """
        INSERT INTO torres (id, complejo_id, nombre, descripcion, numero_pisos)
        SELECT
            gen_random_uuid(),
            complejos.id,
            'Torre principal',
            'Torre creada automáticamente para pisos existentes.',
            LEAST(99, GREATEST(1, COUNT(pisos.id)))
        FROM complejos
        LEFT JOIN pisos ON pisos.complejo_id = complejos.id
        WHERE NOT EXISTS (
            SELECT 1
            FROM torres
            WHERE torres.complejo_id = complejos.id
        )
        GROUP BY complejos.id
        """
    )
    op.execute(
        """
        UPDATE pisos
        SET torre_id = torres.id
        FROM torres
        WHERE torres.complejo_id = pisos.complejo_id
          AND pisos.torre_id IS NULL
        """
    )
    op.alter_column("pisos", "torre_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)


def downgrade() -> None:
    op.drop_constraint("fk_pisos_torre_id_torres", "pisos", type_="foreignkey")
    op.drop_index("ix_pisos_torre_id", table_name="pisos")
    op.drop_column("pisos", "torre_id")
    op.drop_index("ix_torres_complejo_id", table_name="torres")
    op.drop_table("torres")
