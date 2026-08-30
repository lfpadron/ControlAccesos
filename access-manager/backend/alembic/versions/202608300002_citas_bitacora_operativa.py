"""Agregar bitacora operativa a citas.

Revision ID: 202608300002
Revises: 202608300001
Create Date: 2026-08-30 00:02:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "202608300002"
down_revision = "202608300001"
branch_labels = None
depends_on = None


TIPOS_CHECKIN = "'LECTOR_QR_APP', 'KIOSKO', 'RECEPCION_MANUAL', 'RECEPCION_QR'"
TIPOS_CANCELACION = "'MANUAL', 'SISTEMA'"


def upgrade() -> None:
    op.add_column("citas", sa.Column("fecha_hora_checkin", sa.DateTime(timezone=True), nullable=True))
    op.add_column("citas", sa.Column("fecha_hora_autorizar", sa.DateTime(timezone=True), nullable=True))
    op.add_column("citas", sa.Column("fecha_hora_llamar", sa.DateTime(timezone=True), nullable=True))
    op.add_column("citas", sa.Column("fecha_hora_cancelar", sa.DateTime(timezone=True), nullable=True))
    op.add_column("citas", sa.Column("tipo_checkin", sa.String(length=32), nullable=True))
    op.add_column("citas", sa.Column("usuario_checkin_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("citas", sa.Column("tipo_cancelacion", sa.String(length=24), nullable=True))
    op.add_column("citas", sa.Column("usuario_cancelacion_id", postgresql.UUID(as_uuid=True), nullable=True))

    op.execute(
        """
        WITH latest_checkin AS (
            SELECT DISTINCT ON (cita_id)
                cita_id,
                created_at,
                usuario_id,
                CASE
                    WHEN canal = 'RECEPCION' AND dispositivo_id = 'recepcion-qr' THEN 'RECEPCION_QR'
                    WHEN canal = 'RECEPCION' THEN 'RECEPCION_MANUAL'
                    WHEN canal = 'APP_MOVIL' THEN 'LECTOR_QR_APP'
                    ELSE 'KIOSKO'
                END AS tipo_checkin
            FROM eventos_llegada
            WHERE tipo = 'CHECKIN_LOBBY'
            ORDER BY cita_id, created_at DESC
        )
        UPDATE citas
        SET
            fecha_hora_checkin = latest_checkin.created_at,
            tipo_checkin = latest_checkin.tipo_checkin,
            usuario_checkin_id = latest_checkin.usuario_id
        FROM latest_checkin
        WHERE citas.id = latest_checkin.cita_id
        """
    )
    op.execute(
        """
        WITH latest_call AS (
            SELECT cita_id, MAX(llamado_en) AS llamado_en
            FROM turnos_display
            WHERE cita_id IS NOT NULL
            GROUP BY cita_id
        )
        UPDATE citas
        SET fecha_hora_llamar = latest_call.llamado_en
        FROM latest_call
        WHERE citas.id = latest_call.cita_id
        """
    )
    op.execute(
        """
        WITH latest_authorization AS (
            SELECT DISTINCT ON (entidad_id)
                entidad_id,
                created_at
            FROM auditoria
            WHERE entidad = 'citas'
              AND evento = 'ACCESO_AUTORIZADO'
              AND entidad_id IS NOT NULL
            ORDER BY entidad_id, created_at DESC
        )
        UPDATE citas
        SET fecha_hora_autorizar = latest_authorization.created_at
        FROM latest_authorization
        WHERE citas.id = latest_authorization.entidad_id
        """
    )
    op.execute(
        """
        WITH latest_cancellation AS (
            SELECT DISTINCT ON (entidad_id)
                entidad_id,
                created_at,
                usuario_id
            FROM auditoria
            WHERE entidad = 'citas'
              AND evento = 'CITA_CANCELADA'
              AND entidad_id IS NOT NULL
            ORDER BY entidad_id, created_at DESC
        )
        UPDATE citas
        SET
            fecha_hora_cancelar = latest_cancellation.created_at,
            tipo_cancelacion = 'MANUAL',
            usuario_cancelacion_id = latest_cancellation.usuario_id
        FROM latest_cancellation
        WHERE citas.id = latest_cancellation.entidad_id
        """
    )

    op.create_check_constraint(
        "ck_citas_tipo_checkin_valido",
        "citas",
        f"tipo_checkin IS NULL OR tipo_checkin IN ({TIPOS_CHECKIN})",
    )
    op.create_check_constraint(
        "ck_citas_tipo_cancelacion_valido",
        "citas",
        f"tipo_cancelacion IS NULL OR tipo_cancelacion IN ({TIPOS_CANCELACION})",
    )
    op.create_foreign_key(
        "fk_citas_usuario_checkin_id_usuarios",
        "citas",
        "usuarios",
        ["usuario_checkin_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_citas_usuario_cancelacion_id_usuarios",
        "citas",
        "usuarios",
        ["usuario_cancelacion_id"],
        ["id"],
    )
    op.create_index("ix_citas_fecha_hora_checkin", "citas", ["fecha_hora_checkin"])
    op.create_index("ix_citas_fecha_hora_llamar", "citas", ["fecha_hora_llamar"])
    op.create_index("ix_citas_fecha_hora_cancelar", "citas", ["fecha_hora_cancelar"])
    op.create_index("ix_citas_usuario_checkin_id", "citas", ["usuario_checkin_id"])
    op.create_index("ix_citas_usuario_cancelacion_id", "citas", ["usuario_cancelacion_id"])


def downgrade() -> None:
    op.drop_index("ix_citas_usuario_cancelacion_id", table_name="citas")
    op.drop_index("ix_citas_usuario_checkin_id", table_name="citas")
    op.drop_index("ix_citas_fecha_hora_cancelar", table_name="citas")
    op.drop_index("ix_citas_fecha_hora_llamar", table_name="citas")
    op.drop_index("ix_citas_fecha_hora_checkin", table_name="citas")
    op.drop_constraint("fk_citas_usuario_cancelacion_id_usuarios", "citas", type_="foreignkey")
    op.drop_constraint("fk_citas_usuario_checkin_id_usuarios", "citas", type_="foreignkey")
    op.drop_constraint("ck_citas_tipo_cancelacion_valido", "citas", type_="check")
    op.drop_constraint("ck_citas_tipo_checkin_valido", "citas", type_="check")
    op.drop_column("citas", "usuario_cancelacion_id")
    op.drop_column("citas", "tipo_cancelacion")
    op.drop_column("citas", "usuario_checkin_id")
    op.drop_column("citas", "tipo_checkin")
    op.drop_column("citas", "fecha_hora_cancelar")
    op.drop_column("citas", "fecha_hora_llamar")
    op.drop_column("citas", "fecha_hora_autorizar")
    op.drop_column("citas", "fecha_hora_checkin")
