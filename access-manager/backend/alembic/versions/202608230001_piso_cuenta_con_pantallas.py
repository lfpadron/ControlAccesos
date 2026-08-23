"""Agregar bandera de pantallas por piso.

Revision ID: 202608230001
Revises: 202608210002
Create Date: 2026-08-23
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "202608230001"
down_revision = "202608210002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pisos",
        sa.Column("cuenta_con_pantallas", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.execute(
        """
        UPDATE pisos
        SET cuenta_con_pantallas = true
        WHERE id IN (
            SELECT DISTINCT piso_id
            FROM pantallas_turnos
            WHERE piso_id IS NOT NULL
              AND activa IS TRUE
        )
        """
    )
    op.execute(
        """
        DELETE FROM consultorios_clusters cc
        USING consultorios c
        JOIN pisos p ON p.id = c.piso_id
        WHERE cc.consultorio_id = c.id
          AND p.cuenta_con_pantallas IS FALSE
        """
    )
    op.execute(
        """
        UPDATE roles
        SET permisos = (
            COALESCE(permisos, '{}'::json)::jsonb || '{"recepcion": "editar"}'::jsonb
        )::json
        WHERE codigo = 'RECEPCIONISTA'
          AND NOT (COALESCE(permisos, '{}'::json)::jsonb ? 'recepcion')
        """
    )
    op.execute(
        """
        UPDATE roles
        SET permisos = (
            COALESCE(permisos, '{}'::json)::jsonb || '{"checkin-qr": "editar"}'::jsonb
        )::json
        WHERE codigo = 'RECEPCIONISTA'
          AND NOT (COALESCE(permisos, '{}'::json)::jsonb ? 'checkin-qr')
        """
    )


def downgrade() -> None:
    op.drop_column("pisos", "cuenta_con_pantallas")
