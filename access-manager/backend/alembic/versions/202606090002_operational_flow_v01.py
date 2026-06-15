"""operational flow v01

Revision ID: 202606090002
Revises: 202606090001
Create Date: 2026-06-09 00:02:00.000000
"""

from __future__ import annotations

from datetime import time
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202606090002"
down_revision = "202606090001"
branch_labels = None
depends_on = None

ALPHABET = "ACDEFGHJKMNPQRTWXY234679"


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    ]


def code_for(index: int) -> str:
    base = len(ALPHABET)
    value = index + 17
    chars: list[str] = []
    for _ in range(4):
        chars.append(ALPHABET[value % base])
        value //= base
    return "".join(chars)


def upgrade() -> None:
    op.create_table(
        "pacientes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("folio_paciente", sa.String(length=24), nullable=False),
        sa.Column("nombre", sa.String(length=180), nullable=False),
        sa.Column("apellido_paterno", sa.String(length=180), nullable=False),
        sa.Column("apellido_materno", sa.String(length=180), nullable=True),
        sa.Column("celular", sa.String(length=40), nullable=True),
        sa.Column("fecha_nacimiento", sa.Date(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *timestamps(),
        sa.CheckConstraint("celular IS NOT NULL OR fecha_nacimiento IS NOT NULL", name="ck_pacientes_contacto_o_fecha_nacimiento"),
        sa.UniqueConstraint("folio_paciente", name="uq_pacientes_folio_paciente"),
    )
    op.create_index("ix_pacientes_folio_paciente", "pacientes", ["folio_paciente"])
    op.create_index("ix_pacientes_celular", "pacientes", ["celular"])

    op.add_column("citas", sa.Column("tipo", sa.String(length=24), nullable=True))
    op.add_column("citas", sa.Column("paciente_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("citas", sa.Column("medico_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("citas", sa.Column("sala_prevista_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("citas", sa.Column("fecha_cita", sa.Date(), nullable=True))
    op.add_column("citas", sa.Column("hora_cita", sa.Time(), nullable=True))
    op.add_column("citas", sa.Column("duracion_estimada", sa.Integer(), nullable=True))
    op.add_column("citas", sa.Column("folio_turno", sa.String(length=4), nullable=True))
    op.add_column("citas", sa.Column("origen", sa.String(length=80), nullable=True))
    op.add_column("citas", sa.Column("notas_operativas", sa.Text(), nullable=True))
    op.add_column("citas", sa.Column("creada_por", postgresql.UUID(as_uuid=True), nullable=True))

    conn = op.get_bind()
    has_citas = conn.scalar(sa.text("SELECT EXISTS (SELECT 1 FROM citas)"))
    if has_citas:
        paciente_id = conn.scalar(sa.text("SELECT id FROM pacientes WHERE folio_paciente = 'PDEMO246'"))
        if paciente_id is None:
            paciente_id = uuid.uuid4()
            conn.execute(
                sa.text(
                    """
                    INSERT INTO pacientes (
                        id, folio_paciente, nombre, apellido_paterno, apellido_materno,
                        celular, fecha_nacimiento, activo, created_at, updated_at
                    )
                    VALUES (:id, 'PDEMO246', 'Paciente', 'Demo', NULL, '5550100000', NULL, true, now(), now())
                    """
                ),
                {"id": paciente_id},
            )

        medico_id = conn.scalar(sa.text("SELECT id FROM medicos ORDER BY created_at LIMIT 1"))
        if medico_id is None:
            medico_id = uuid.uuid4()
            conn.execute(
                sa.text(
                    """
                    INSERT INTO medicos (id, nombre, apellidos, nombre_visible, activo, created_at, updated_at)
                    VALUES (:id, 'Médico', 'Migración', 'Dr. Migración', true, now(), now())
                    """
                ),
                {"id": medico_id},
            )

        rows = list(conn.execute(sa.text("SELECT id, turno FROM citas ORDER BY created_at, id")).mappings())
        for index, row in enumerate(rows):
            old_turn = (row["turno"] or "").upper()
            folio = old_turn if len(old_turn) == 4 and all(char in ALPHABET for char in old_turn) else code_for(index)
            conn.execute(
                sa.text(
                    """
                    UPDATE citas
                    SET tipo = 'PROGRAMADA',
                        estado = CASE WHEN estado = 'PROGRAMADA' THEN 'AGENDADA' ELSE estado END,
                        paciente_id = :paciente_id,
                        medico_id = :medico_id,
                        piso_id = COALESCE(piso_id, (SELECT piso_id FROM consultorios WHERE consultorios.id = citas.consultorio_id)),
                        fecha_cita = CURRENT_DATE,
                        hora_cita = :hora_cita,
                        folio_turno = :folio
                    WHERE id = :id
                    """
                ),
                {"id": row["id"], "paciente_id": paciente_id, "medico_id": medico_id, "hora_cita": time(9, 0), "folio": folio},
            )

    op.execute("UPDATE citas SET tipo = 'PROGRAMADA' WHERE tipo IS NULL")
    op.execute("UPDATE citas SET estado = 'AGENDADA' WHERE estado = 'PROGRAMADA'")
    op.execute("UPDATE citas SET fecha_cita = CURRENT_DATE WHERE fecha_cita IS NULL")
    op.execute("UPDATE citas SET hora_cita = TIME '09:00' WHERE hora_cita IS NULL")
    op.execute("UPDATE citas SET folio_turno = 'T4CN' WHERE folio_turno IS NULL")

    op.alter_column("citas", "tipo", nullable=False)
    op.alter_column("citas", "estado", server_default="AGENDADA", existing_type=sa.String(length=40), nullable=False)
    op.alter_column("citas", "paciente_id", nullable=False)
    op.alter_column("citas", "medico_id", nullable=False)
    op.alter_column("citas", "piso_id", nullable=False)
    op.alter_column("citas", "fecha_cita", nullable=False)
    op.alter_column("citas", "hora_cita", nullable=False)
    op.alter_column("citas", "folio_turno", nullable=False)

    op.create_index("ix_citas_paciente_id", "citas", ["paciente_id"])
    op.create_index("ix_citas_medico_id", "citas", ["medico_id"])
    op.create_index("ix_citas_sala_prevista_id", "citas", ["sala_prevista_id"])
    op.create_index("ix_citas_fecha_cita", "citas", ["fecha_cita"])
    op.create_index("ix_citas_creada_por", "citas", ["creada_por"])
    op.create_foreign_key("fk_citas_paciente_id_pacientes", "citas", "pacientes", ["paciente_id"], ["id"])
    op.create_foreign_key("fk_citas_medico_id_medicos", "citas", "medicos", ["medico_id"], ["id"])
    op.create_foreign_key("fk_citas_sala_prevista_id_salas_espera", "citas", "salas_espera", ["sala_prevista_id"], ["id"])
    op.create_foreign_key("fk_citas_creada_por_usuarios", "citas", "usuarios", ["creada_por"], ["id"])
    op.create_unique_constraint("uq_citas_complejo_fecha_folio", "citas", ["complejo_id", "fecha_cita", "folio_turno"])
    op.create_check_constraint("ck_citas_tipo_valido", "citas", "tipo IN ('PROGRAMADA', 'ESPONTANEA')")
    op.create_check_constraint(
        "ck_citas_estado_valido",
        "citas",
        "estado IN ('AGENDADA', 'QR_GENERADO', 'LLEGO_LOBBY', 'AUTORIZADO_PASAR', 'EN_CONSULTA', 'FINALIZADA', 'NO_LLEGO', 'CANCELADA', 'EXPIRADA')",
    )
    op.drop_column("citas", "turno")

    op.create_table(
        "qr_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("cita_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("estado", sa.String(length=24), nullable=False, server_default="GENERADO"),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("fecha_emision", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_expiracion", sa.DateTime(timezone=True), nullable=False),
        *timestamps(),
        sa.CheckConstraint("estado IN ('GENERADO', 'USADO', 'EXPIRADO', 'CANCELADO')", name="ck_qr_tokens_estado_valido"),
        sa.ForeignKeyConstraint(["cita_id"], ["citas.id"], name="fk_qr_tokens_cita_id_citas"),
    )
    op.create_index("ix_qr_tokens_cita_id", "qr_tokens", ["cita_id"])
    op.create_index("ix_qr_tokens_token_hash", "qr_tokens", ["token_hash"])

    op.create_table(
        "eventos_llegada",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("cita_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("sala_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("canal", sa.String(length=32), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dispositivo_id", sa.String(length=120), nullable=True),
        sa.Column("ip_origen", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("tipo IN ('CHECKIN_LOBBY', 'CHECKIN_SALA')", name="ck_eventos_llegada_tipo_valido"),
        sa.CheckConstraint(
            "canal IN ('KIOSKO', 'RECEPCION', 'OPERADOR', 'APP_MOVIL', 'BOT_TELEGRAM', 'API_EXTERNA')",
            name="ck_eventos_llegada_canal_valido",
        ),
        sa.ForeignKeyConstraint(["cita_id"], ["citas.id"], name="fk_eventos_llegada_cita_id_citas"),
        sa.ForeignKeyConstraint(["sala_id"], ["salas_espera.id"], name="fk_eventos_llegada_sala_id_salas_espera"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], name="fk_eventos_llegada_usuario_id_usuarios"),
    )
    op.create_index("ix_eventos_llegada_cita_id", "eventos_llegada", ["cita_id"])
    op.create_index("ix_eventos_llegada_sala_id", "eventos_llegada", ["sala_id"])
    op.create_index("ix_eventos_llegada_usuario_id", "eventos_llegada", ["usuario_id"])


def downgrade() -> None:
    op.drop_table("eventos_llegada")
    op.drop_table("qr_tokens")
    op.add_column("citas", sa.Column("turno", sa.String(length=40), nullable=True))
    op.execute("UPDATE citas SET turno = folio_turno")
    op.alter_column("citas", "turno", nullable=False)
    op.drop_constraint("ck_citas_estado_valido", "citas", type_="check")
    op.drop_constraint("ck_citas_tipo_valido", "citas", type_="check")
    op.drop_constraint("uq_citas_complejo_fecha_folio", "citas", type_="unique")
    op.drop_constraint("fk_citas_creada_por_usuarios", "citas", type_="foreignkey")
    op.drop_constraint("fk_citas_sala_prevista_id_salas_espera", "citas", type_="foreignkey")
    op.drop_constraint("fk_citas_medico_id_medicos", "citas", type_="foreignkey")
    op.drop_constraint("fk_citas_paciente_id_pacientes", "citas", type_="foreignkey")
    op.drop_index("ix_citas_creada_por", table_name="citas")
    op.drop_index("ix_citas_fecha_cita", table_name="citas")
    op.drop_index("ix_citas_sala_prevista_id", table_name="citas")
    op.drop_index("ix_citas_medico_id", table_name="citas")
    op.drop_index("ix_citas_paciente_id", table_name="citas")
    for column in (
        "creada_por",
        "notas_operativas",
        "origen",
        "folio_turno",
        "duracion_estimada",
        "hora_cita",
        "fecha_cita",
        "sala_prevista_id",
        "medico_id",
        "paciente_id",
        "tipo",
    ):
        op.drop_column("citas", column)
    op.alter_column("citas", "piso_id", nullable=True)
    op.alter_column("citas", "estado", server_default="PROGRAMADA", existing_type=sa.String(length=40), nullable=False)
    op.drop_table("pacientes")
