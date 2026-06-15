"""clusters turnos

Revision ID: 202606100002
Revises: 202606100001
Create Date: 2026-06-10 00:02:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202606100002"
down_revision = "202606100001"
branch_labels = None
depends_on = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    ]


def upgrade() -> None:
    op.create_table(
        "clusters_turnos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("complejo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("piso_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=180), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *timestamps(),
        sa.ForeignKeyConstraint(["complejo_id"], ["complejos.id"], name="fk_clusters_turnos_complejo_id"),
        sa.ForeignKeyConstraint(["piso_id"], ["pisos.id"], name="fk_clusters_turnos_piso_id"),
        sa.UniqueConstraint("piso_id", "nombre", name="uq_clusters_turnos_piso_nombre"),
    )
    op.create_index("ix_clusters_turnos_complejo_id", "clusters_turnos", ["complejo_id"])
    op.create_index("ix_clusters_turnos_piso_id", "clusters_turnos", ["piso_id"])

    op.create_table(
        "consultorios_clusters",
        sa.Column("consultorio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["consultorio_id"], ["consultorios.id"], ondelete="CASCADE", name="fk_consultorios_clusters_consultorio_id"),
        sa.ForeignKeyConstraint(["cluster_id"], ["clusters_turnos.id"], ondelete="CASCADE", name="fk_consultorios_clusters_cluster_id"),
        sa.PrimaryKeyConstraint("consultorio_id", "cluster_id", name="pk_consultorios_clusters"),
    )
    op.create_index("ix_consultorios_clusters_cluster_id", "consultorios_clusters", ["cluster_id"])

    op.create_table(
        "pantallas_turnos_clusters",
        sa.Column("pantalla_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["pantalla_id"], ["pantallas_turnos.id"], ondelete="CASCADE", name="fk_pantallas_turnos_clusters_pantalla_id"),
        sa.ForeignKeyConstraint(["cluster_id"], ["clusters_turnos.id"], ondelete="CASCADE", name="fk_pantallas_turnos_clusters_cluster_id"),
        sa.PrimaryKeyConstraint("pantalla_id", "cluster_id", name="pk_pantallas_turnos_clusters"),
    )
    op.create_index("ix_pantallas_turnos_clusters_cluster_id", "pantallas_turnos_clusters", ["cluster_id"])

    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute(
        """
        INSERT INTO clusters_turnos (id, complejo_id, piso_id, nombre, descripcion)
        SELECT gen_random_uuid(), pisos.complejo_id, pisos.id, 'Clúster principal', 'Clúster creado automáticamente para registros existentes.'
        FROM pisos
        WHERE NOT EXISTS (
            SELECT 1
            FROM clusters_turnos
            WHERE clusters_turnos.piso_id = pisos.id
        )
        """
    )
    op.execute(
        """
        INSERT INTO consultorios_clusters (consultorio_id, cluster_id)
        SELECT consultorios.id, clusters_turnos.id
        FROM consultorios
        JOIN clusters_turnos
            ON clusters_turnos.complejo_id = consultorios.complejo_id
            AND clusters_turnos.piso_id = consultorios.piso_id
        WHERE clusters_turnos.nombre = 'Clúster principal'
        ON CONFLICT DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO pantallas_turnos_clusters (pantalla_id, cluster_id)
        SELECT pantallas_turnos.id, clusters_turnos.id
        FROM pantallas_turnos
        JOIN clusters_turnos
            ON clusters_turnos.complejo_id = pantallas_turnos.complejo_id
            AND clusters_turnos.piso_id = pantallas_turnos.piso_id
        WHERE clusters_turnos.nombre = 'Clúster principal'
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_pantallas_turnos_clusters_cluster_id", table_name="pantallas_turnos_clusters")
    op.drop_table("pantallas_turnos_clusters")
    op.drop_index("ix_consultorios_clusters_cluster_id", table_name="consultorios_clusters")
    op.drop_table("consultorios_clusters")
    op.drop_index("ix_clusters_turnos_piso_id", table_name="clusters_turnos")
    op.drop_index("ix_clusters_turnos_complejo_id", table_name="clusters_turnos")
    op.drop_table("clusters_turnos")
