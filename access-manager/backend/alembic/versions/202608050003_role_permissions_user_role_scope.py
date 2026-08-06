"""Permisos por rol y alcance ampliado de usuario roles.

Revision ID: 202608050003
Revises: 202608050002
Create Date: 2026-08-05
"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202608050003"
down_revision = "202608050002"
branch_labels = None
depends_on = None


SCREEN_KEYS = [
    "dashboard",
    "perfil",
    "instituciones",
    "campus",
    "torres",
    "pisos",
    "salas-espera",
    "clusters-turnos",
    "consultorios",
    "consulta-clusters-consultorios",
    "usuarios",
    "busqueda-usuarios",
    "roles",
    "usuario-roles",
    "medicos",
    "operadores",
    "pacientes",
    "citas",
    "citas-hoy",
    "contactos-institucionales",
    "asignaciones",
    "pantallas-turnos",
    "kioskos",
    "turnos-llamados",
    "reportes",
    "auditoria",
]


def upgrade() -> None:
    op.add_column("roles", sa.Column("permisos", sa.JSON(), server_default=sa.text("'{}'"), nullable=True))
    admin_permissions = json.dumps({screen: "editar" for screen in SCREEN_KEYS})
    op.execute(f"UPDATE roles SET permisos = '{admin_permissions}' WHERE codigo = 'ADMIN_SISTEMA'")

    op.add_column("usuario_roles", sa.Column("torre_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("usuario_roles", sa.Column("piso_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("usuario_roles", sa.Column("consultorio_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("usuario_roles", sa.Column("medico_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_usuario_roles_torre_id", "usuario_roles", ["torre_id"])
    op.create_index("ix_usuario_roles_piso_id", "usuario_roles", ["piso_id"])
    op.create_index("ix_usuario_roles_consultorio_id", "usuario_roles", ["consultorio_id"])
    op.create_index("ix_usuario_roles_medico_id", "usuario_roles", ["medico_id"])
    op.create_foreign_key("fk_usuario_roles_torre_id", "usuario_roles", "torres", ["torre_id"], ["id"])
    op.create_foreign_key("fk_usuario_roles_piso_id", "usuario_roles", "pisos", ["piso_id"], ["id"])
    op.create_foreign_key("fk_usuario_roles_consultorio_id", "usuario_roles", "consultorios", ["consultorio_id"], ["id"])
    op.create_foreign_key("fk_usuario_roles_medico_id", "usuario_roles", "medicos", ["medico_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_usuario_roles_medico_id", "usuario_roles", type_="foreignkey")
    op.drop_constraint("fk_usuario_roles_consultorio_id", "usuario_roles", type_="foreignkey")
    op.drop_constraint("fk_usuario_roles_piso_id", "usuario_roles", type_="foreignkey")
    op.drop_constraint("fk_usuario_roles_torre_id", "usuario_roles", type_="foreignkey")
    op.drop_index("ix_usuario_roles_medico_id", table_name="usuario_roles")
    op.drop_index("ix_usuario_roles_consultorio_id", table_name="usuario_roles")
    op.drop_index("ix_usuario_roles_piso_id", table_name="usuario_roles")
    op.drop_index("ix_usuario_roles_torre_id", table_name="usuario_roles")
    op.drop_column("usuario_roles", "medico_id")
    op.drop_column("usuario_roles", "consultorio_id")
    op.drop_column("usuario_roles", "piso_id")
    op.drop_column("usuario_roles", "torre_id")
    op.drop_column("roles", "permisos")
