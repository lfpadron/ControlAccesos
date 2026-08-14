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
        UPDATE medicos
        SET
            usuario_id = usuarios.id,
            nombre = usuarios.nombre,
            apellidos = usuarios.apellidos,
            nombre_visible = NULL,
            activo = true,
            updated_at = now()
        FROM usuario_roles
        JOIN roles ON roles.id = usuario_roles.rol_id
        JOIN usuarios ON usuarios.id = usuario_roles.usuario_id
        WHERE medicos.id = usuario_roles.medico_id
          AND roles.codigo = 'MEDICO'
          AND roles.activo IS TRUE
          AND usuario_roles.activo IS TRUE
          AND usuario_roles.fecha_inicio <= CURRENT_DATE
          AND (usuario_roles.fecha_fin IS NULL OR usuario_roles.fecha_fin >= CURRENT_DATE)
          AND upper(usuarios.estado) = 'ACTIVO'
        """
    )
    op.execute(
        """
        WITH medico_users AS (
            SELECT DISTINCT usuarios.id, usuarios.nombre, usuarios.apellidos, usuarios.email
            FROM usuarios
            JOIN usuario_roles ON usuario_roles.usuario_id = usuarios.id
            JOIN roles ON roles.id = usuario_roles.rol_id
            WHERE roles.codigo = 'MEDICO'
              AND roles.activo IS TRUE
              AND usuario_roles.activo IS TRUE
              AND usuario_roles.fecha_inicio <= CURRENT_DATE
              AND (usuario_roles.fecha_fin IS NULL OR usuario_roles.fecha_fin >= CURRENT_DATE)
              AND upper(usuarios.estado) = 'ACTIVO'
        ),
        matches AS (
            SELECT DISTINCT ON (medicos.id)
                medicos.id AS medico_id,
                medico_users.id AS usuario_id,
                medico_users.nombre,
                medico_users.apellidos
            FROM medicos
            JOIN medico_users ON (
                regexp_replace(
                    lower(translate(coalesce(medicos.nombre, '') || ' ' || coalesce(medicos.apellidos, ''), 'áéíóúüñÁÉÍÓÚÜÑ', 'aeiouunAEIOUUN')),
                    '[^a-z0-9]+',
                    ' ',
                    'g'
                ) = regexp_replace(lower(split_part(medico_users.email, '@', 1)), '[^a-z0-9]+', ' ', 'g')
                OR regexp_replace(
                    lower(translate(coalesce(medico_users.nombre, '') || ' ' || coalesce(medico_users.apellidos, ''), 'áéíóúüñÁÉÍÓÚÜÑ', 'aeiouunAEIOUUN')),
                    '[^a-z0-9]+',
                    ' ',
                    'g'
                ) = regexp_replace(
                    lower(translate(coalesce(medicos.nombre, '') || ' ' || coalesce(medicos.apellidos, ''), 'áéíóúüñÁÉÍÓÚÜÑ', 'aeiouunAEIOUUN')),
                    '[^a-z0-9]+',
                    ' ',
                    'g'
                )
            )
            WHERE medicos.usuario_id IS NULL
              AND medicos.activo IS TRUE
            ORDER BY medicos.id
        )
        UPDATE medicos
        SET
            usuario_id = matches.usuario_id,
            nombre = matches.nombre,
            apellidos = matches.apellidos,
            nombre_visible = NULL,
            activo = true,
            updated_at = now()
        FROM matches
        WHERE medicos.id = matches.medico_id
        """
    )
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
    op.execute(
        """
        CREATE TEMP TABLE tmp_medico_duplicates ON COMMIT DROP AS
        WITH scored AS (
            SELECT
                medicos.id,
                medicos.usuario_id,
                (
                    (SELECT count(*) FROM medico_pacientes WHERE medico_pacientes.medico_id = medicos.id) +
                    (SELECT count(*) FROM citas WHERE citas.medico_id = medicos.id) +
                    (SELECT count(*) FROM usuario_roles WHERE usuario_roles.medico_id = medicos.id) +
                    (SELECT count(*) FROM asignaciones_medico_consultorio WHERE asignaciones_medico_consultorio.medico_id = medicos.id) +
                    (SELECT count(*) FROM asignaciones_operador WHERE asignaciones_operador.medico_id = medicos.id)
                ) AS refs,
                row_number() OVER (
                    PARTITION BY medicos.usuario_id
                    ORDER BY
                        (
                            (SELECT count(*) FROM medico_pacientes WHERE medico_pacientes.medico_id = medicos.id) +
                            (SELECT count(*) FROM citas WHERE citas.medico_id = medicos.id) +
                            (SELECT count(*) FROM usuario_roles WHERE usuario_roles.medico_id = medicos.id) +
                            (SELECT count(*) FROM asignaciones_medico_consultorio WHERE asignaciones_medico_consultorio.medico_id = medicos.id) +
                            (SELECT count(*) FROM asignaciones_operador WHERE asignaciones_operador.medico_id = medicos.id)
                        ) DESC,
                        medicos.activo DESC,
                        medicos.updated_at DESC,
                        medicos.id
                ) AS rn
            FROM medicos
            WHERE medicos.usuario_id IS NOT NULL
        ),
        canonical AS (
            SELECT usuario_id, id AS target_id
            FROM scored
            WHERE rn = 1
        )
        SELECT scored.id AS source_id, canonical.target_id
        FROM scored
        JOIN canonical ON canonical.usuario_id = scored.usuario_id
        WHERE scored.rn > 1
        """
    )
    op.execute(
        """
        DELETE FROM medico_pacientes
        USING tmp_medico_duplicates
        WHERE medico_pacientes.medico_id = tmp_medico_duplicates.source_id
          AND EXISTS (
              SELECT 1
              FROM medico_pacientes target
              WHERE target.medico_id = tmp_medico_duplicates.target_id
                AND target.paciente_id = medico_pacientes.paciente_id
          )
        """
    )
    op.execute(
        """
        UPDATE medico_pacientes
        SET medico_id = tmp_medico_duplicates.target_id
        FROM tmp_medico_duplicates
        WHERE medico_pacientes.medico_id = tmp_medico_duplicates.source_id
        """
    )
    op.execute(
        """
        UPDATE citas
        SET medico_id = tmp_medico_duplicates.target_id
        FROM tmp_medico_duplicates
        WHERE citas.medico_id = tmp_medico_duplicates.source_id
        """
    )
    op.execute(
        """
        UPDATE usuario_roles
        SET medico_id = tmp_medico_duplicates.target_id
        FROM tmp_medico_duplicates
        WHERE usuario_roles.medico_id = tmp_medico_duplicates.source_id
        """
    )
    op.execute(
        """
        UPDATE asignaciones_medico_consultorio
        SET medico_id = tmp_medico_duplicates.target_id
        FROM tmp_medico_duplicates
        WHERE asignaciones_medico_consultorio.medico_id = tmp_medico_duplicates.source_id
        """
    )
    op.execute(
        """
        UPDATE asignaciones_operador
        SET medico_id = tmp_medico_duplicates.target_id
        FROM tmp_medico_duplicates
        WHERE asignaciones_operador.medico_id = tmp_medico_duplicates.source_id
        """
    )
    op.execute(
        """
        UPDATE medicos AS target
        SET plantilla_turno = source.plantilla_turno, updated_at = now()
        FROM tmp_medico_duplicates
        JOIN medicos AS source ON source.id = tmp_medico_duplicates.source_id
        WHERE target.id = tmp_medico_duplicates.target_id
          AND target.plantilla_turno = 'PACIENTE_CONSULTORIO'
          AND source.plantilla_turno <> 'PACIENTE_CONSULTORIO'
        """
    )
    op.execute(
        """
        UPDATE medicos
        SET usuario_id = NULL, activo = false, updated_at = now()
        FROM tmp_medico_duplicates
        WHERE medicos.id = tmp_medico_duplicates.source_id
        """
    )
    op.execute(
        """
        UPDATE medicos
        SET nombre = usuarios.nombre, apellidos = usuarios.apellidos, nombre_visible = NULL, activo = true, updated_at = now()
        FROM usuarios
        WHERE medicos.usuario_id = usuarios.id
        """
    )
    op.execute(
        """
        WITH rendered AS (
            SELECT
                turnos_display.id,
                citas.folio_turno,
                medicos.plantilla_turno,
                coalesce(consultorios.nombre_visible, consultorios.codigo, 'Consultorio') AS consultorio_label,
                btrim(
                    concat(
                        coalesce(nullif(pacientes.nombre_preferido, ''), nullif(pacientes.nombre, ''), 'Paciente'),
                        ' ',
                        upper(left(coalesce(pacientes.apellido_paterno, ''), 1)),
                        '*'
                    )
                ) AS patient_text
            FROM turnos_display
            JOIN citas ON citas.id = turnos_display.cita_id
            JOIN medicos ON medicos.id = citas.medico_id
            LEFT JOIN pacientes ON pacientes.id = citas.paciente_id
            LEFT JOIN consultorios ON consultorios.id = citas.consultorio_id
        ),
        destinations AS (
            SELECT
                id,
                folio_turno,
                plantilla_turno,
                consultorio_label,
                patient_text,
                CASE
                    WHEN lower(left(consultorio_label, 11)) = 'consultorio'
                    THEN 'consultorio' || substring(consultorio_label FROM 12)
                    ELSE 'consultorio ' || consultorio_label
                END AS destination_text
            FROM rendered
        )
        UPDATE turnos_display
        SET
            consultorio = destinations.consultorio_label,
            texto_visible = CASE destinations.plantilla_turno
                WHEN 'TURNO_PACIENTE_CONSULTORIO'
                THEN 'Turno ' || destinations.folio_turno || ' del paciente ' || destinations.patient_text || ' a ' || destinations.destination_text
                WHEN 'PACIENTE_TURNO_CONSULTORIO'
                THEN 'Paciente ' || destinations.patient_text || ' con turno ' || destinations.folio_turno || ' a ' || destinations.destination_text
                WHEN 'TURNO_CONSULTORIO'
                THEN 'Turno ' || destinations.folio_turno || ' a ' || destinations.destination_text
                ELSE 'Paciente ' || destinations.patient_text || ' a ' || destinations.destination_text
            END,
            updated_at = now()
        FROM destinations
        WHERE turnos_display.id = destinations.id
        """
    )


def downgrade() -> None:
    pass
