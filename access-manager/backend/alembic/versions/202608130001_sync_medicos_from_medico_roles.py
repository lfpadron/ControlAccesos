"""Sincroniza medicos desde usuarios con rol medico.

Revision ID: 202608130001
Revises: 202608120001
Create Date: 2026-08-13
"""

from __future__ import annotations

from alembic import op

revision = "202608130001"
down_revision = "202608120001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute(
        """
        INSERT INTO medicos (id, usuario_id, nombre, apellidos, nombre_visible, plantilla_turno, activo, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            usuarios.id,
            usuarios.nombre,
            usuarios.apellidos,
            NULL,
            'PACIENTE_CONSULTORIO',
            true,
            now(),
            now()
        FROM usuarios
        JOIN usuario_roles ON usuario_roles.usuario_id = usuarios.id
        JOIN roles ON roles.id = usuario_roles.rol_id
        WHERE roles.codigo = 'MEDICO'
          AND roles.activo IS TRUE
          AND usuario_roles.activo IS TRUE
          AND usuario_roles.fecha_inicio <= CURRENT_DATE
          AND (usuario_roles.fecha_fin IS NULL OR usuario_roles.fecha_fin >= CURRENT_DATE)
          AND upper(usuarios.estado) = 'ACTIVO'
          AND NOT EXISTS (
              SELECT 1
              FROM medicos
              WHERE medicos.usuario_id = usuarios.id
          )
        GROUP BY usuarios.id, usuarios.nombre, usuarios.apellidos
        """
    )


def downgrade() -> None:
    pass
