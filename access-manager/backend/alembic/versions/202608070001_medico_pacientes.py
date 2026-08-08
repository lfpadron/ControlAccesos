"""Agenda de pacientes por medico.

Revision ID: 202608070001
Revises: 202608050003
Create Date: 2026-08-07
"""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202608070001"
down_revision = "202608050003"
branch_labels = None
depends_on = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    ]


def upgrade() -> None:
    op.create_table(
        "medico_pacientes",
        sa.Column("medico_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("paciente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *timestamps(),
        sa.ForeignKeyConstraint(["medico_id"], ["medicos.id"], name="fk_medico_pacientes_medico_id_medicos", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["paciente_id"], ["pacientes.id"], name="fk_medico_pacientes_paciente_id_pacientes", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("medico_id", "paciente_id", name="pk_medico_pacientes"),
    )
    op.create_index("ix_medico_pacientes_paciente_id", "medico_pacientes", ["paciente_id"])

    conn = op.get_bind()
    demo_medico_id = conn.scalar(
        sa.text(
            """
            SELECT id
            FROM medicos
            WHERE nombre_visible = 'Dr. Demo'
               OR (nombre = 'Médico' AND apellidos = 'Demo')
            ORDER BY created_at
            LIMIT 1
            """
        )
    )
    if demo_medico_id is None:
        demo_medico_id = uuid.uuid4()
        conn.execute(
            sa.text(
                """
                INSERT INTO medicos (
                    id, nombre, apellidos, nombre_visible, plantilla_turno, activo, created_at, updated_at
                )
                VALUES (
                    :id, 'Médico', 'Demo', 'Dr. Demo', 'PACIENTE_CONSULTORIO', true, now(), now()
                )
                """
            ),
            {"id": demo_medico_id},
        )

    conn.execute(
        sa.text(
            """
            INSERT INTO medico_pacientes (medico_id, paciente_id, activo, created_at, updated_at)
            SELECT :medico_id, id, true, now(), now()
            FROM pacientes
            ON CONFLICT (medico_id, paciente_id)
            DO UPDATE SET activo = true, updated_at = now()
            """
        ),
        {"medico_id": demo_medico_id},
    )


def downgrade() -> None:
    op.drop_index("ix_medico_pacientes_paciente_id", table_name="medico_pacientes")
    op.drop_table("medico_pacientes")
