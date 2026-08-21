"""Asignar una institución obligatoria a contactos institucionales.

Revision ID: 202608210002
Revises: 202608210001
Create Date: 2026-08-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202608210002"
down_revision = "202608210001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contactos_institucionales",
        sa.Column("institucion_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_contactos_institucionales_institucion",
        "contactos_institucionales",
        "instituciones",
        ["institucion_id"],
        ["id"],
    )

    op.execute(
        """
        WITH scopes AS (
            SELECT cic.contacto_id, c.institucion_id
            FROM contactos_institucionales_complejos cic
            JOIN complejos c ON c.id = cic.complejo_id
            UNION ALL
            SELECT cit.contacto_id, c.institucion_id
            FROM contactos_institucionales_torres cit
            JOIN torres t ON t.id = cit.torre_id
            JOIN complejos c ON c.id = t.complejo_id
        ),
        selected_scope AS (
            SELECT DISTINCT ON (contacto_id) contacto_id, institucion_id
            FROM scopes
            ORDER BY contacto_id, institucion_id
        )
        UPDATE contactos_institucionales ci
        SET institucion_id = selected_scope.institucion_id
        FROM selected_scope
        WHERE selected_scope.contacto_id = ci.id
        """
    )
    op.execute(
        """
        UPDATE contactos_institucionales
        SET institucion_id = (
            SELECT id
            FROM instituciones
            ORDER BY activo DESC, nombre, id
            LIMIT 1
        )
        WHERE institucion_id IS NULL
        """
    )
    op.alter_column(
        "contactos_institucionales",
        "institucion_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.create_index(
        "ix_contactos_institucionales_institucion_id",
        "contactos_institucionales",
        ["institucion_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_contactos_institucionales_institucion_id", table_name="contactos_institucionales")
    op.drop_constraint(
        "fk_contactos_institucionales_institucion",
        "contactos_institucionales",
        type_="foreignkey",
    )
    op.drop_column("contactos_institucionales", "institucion_id")
