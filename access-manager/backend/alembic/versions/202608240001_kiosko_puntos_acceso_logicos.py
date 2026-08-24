"""Puntos de acceso logicos para kioskos.

Revision ID: 202608240001
Revises: 202608230001
Create Date: 2026-08-24 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "202608240001"
down_revision = "202608230001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("puntos_acceso", sa.Column("torre_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_puntos_acceso_torre_id", "puntos_acceso", "torres", ["torre_id"], ["id"])
    op.create_index("ix_puntos_acceso_torre_id", "puntos_acceso", ["torre_id"])
    op.execute(
        """
        UPDATE puntos_acceso AS pa
        SET torre_id = p.torre_id
        FROM pisos AS p
        WHERE pa.piso_id = p.id
          AND pa.torre_id IS NULL
        """
    )
    op.alter_column(
        "puntos_acceso",
        "piso_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.drop_constraint("uq_puntos_acceso_piso_nombre", "puntos_acceso", type_="unique")
    op.create_unique_constraint(
        "uq_puntos_acceso_scope_nombre",
        "puntos_acceso",
        ["complejo_id", "torre_id", "piso_id", "nombre"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_puntos_acceso_scope_nombre", "puntos_acceso", type_="unique")
    op.execute(
        """
        UPDATE puntos_acceso AS pa
        SET piso_id = p.id
        FROM (
            SELECT DISTINCT ON (complejo_id) id, complejo_id
            FROM pisos
            ORDER BY complejo_id, numero, id
        ) AS p
        WHERE pa.piso_id IS NULL
          AND pa.complejo_id = p.complejo_id
        """
    )
    op.alter_column(
        "puntos_acceso",
        "piso_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.create_unique_constraint("uq_puntos_acceso_piso_nombre", "puntos_acceso", ["piso_id", "nombre"])
    op.drop_index("ix_puntos_acceso_torre_id", table_name="puntos_acceso")
    op.drop_constraint("fk_puntos_acceso_torre_id", "puntos_acceso", type_="foreignkey")
    op.drop_column("puntos_acceso", "torre_id")
