from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.constants import (
    TURNO_TEMPLATE_DEFAULT,
    TURNO_TEMPLATE_PATIENT_CONSULTORIO,
    TURNO_TEMPLATE_PATIENT_TURNO_CONSULTORIO,
    TURNO_TEMPLATE_TURNO_CONSULTORIO,
    TURNO_TEMPLATE_TURNO_PATIENT_CONSULTORIO,
)
from app.models.display import TurnoDisplay
from app.models.flow import Cita, MedicoPaciente, Paciente
from app.models.operational import AsignacionMedicoConsultorio, AsignacionOperador, Consultorio, Medico, Role, UsuarioRol
from app.models.usuario import Usuario


def normalize_identity(value: str | None) -> str:
    import re
    import unicodedata

    normalized = unicodedata.normalize("NFD", value or "")
    without_accents = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    alphanumeric_words = re.sub(r"[^a-zA-Z0-9]+", " ", without_accents)
    return " ".join(alphanumeric_words.lower().split())


def medico_identity_values(medico: Medico) -> set[str]:
    first_last = normalize_identity(f"{medico.nombre} {medico.apellidos}")
    last_first = normalize_identity(f"{medico.apellidos} {medico.nombre}")
    visible = normalize_identity(medico.nombre_visible)
    return {value for value in (first_last, last_first, visible) if value}


def user_identity_values(user: Usuario) -> set[str]:
    email_local = str(user.email).split("@", 1)[0]
    return {
        value
        for value in (
            normalize_identity(f"{user.nombre} {user.apellidos}"),
            normalize_identity(f"{user.apellidos} {user.nombre}"),
            normalize_identity(email_local),
        )
        if value
    }


def consultorio_label(consultorio: Consultorio | None) -> str:
    if consultorio is None:
        return "Consultorio"
    return consultorio.nombre_visible or consultorio.codigo


def consultorio_destination_text(label: str) -> str:
    text = label.strip()
    if text.lower().startswith("consultorio"):
        return f"consultorio{text[len('consultorio'):]}"
    return f"consultorio {text}"


def patient_turn_text(paciente: Paciente | None) -> str:
    if paciente is None:
        return "Paciente *"
    name = (paciente.nombre_preferido or paciente.nombre or "Paciente").strip()
    paternal_initial = (paciente.apellido_paterno or "").strip()[:1].upper()
    return f"{name} {paternal_initial}*".strip()


def render_turno_text(db: Session, cita: Cita) -> str:
    medico = db.get(Medico, cita.medico_id)
    paciente = db.get(Paciente, cita.paciente_id)
    consultorio = db.get(Consultorio, cita.consultorio_id)
    template = getattr(medico, "plantilla_turno", None) or TURNO_TEMPLATE_DEFAULT
    patient = patient_turn_text(paciente)
    destination = consultorio_destination_text(consultorio_label(consultorio))

    if template == TURNO_TEMPLATE_TURNO_PATIENT_CONSULTORIO:
        return f"Turno {cita.folio_turno} del paciente {patient} a {destination}"
    if template == TURNO_TEMPLATE_PATIENT_TURNO_CONSULTORIO:
        return f"Paciente {patient} con turno {cita.folio_turno} a {destination}"
    if template == TURNO_TEMPLATE_TURNO_CONSULTORIO:
        return f"Turno {cita.folio_turno} a {destination}"
    if template == TURNO_TEMPLATE_PATIENT_CONSULTORIO:
        return f"Paciente {patient} a {destination}"
    return f"Paciente {patient} a {destination}"


def refresh_turnos_for_citas(db: Session, cita_ids: set[UUID]) -> None:
    if not cita_ids:
        return
    rows = db.execute(select(TurnoDisplay).where(TurnoDisplay.cita_id.in_(cita_ids))).scalars()
    for row in rows:
        if row.cita_id is None:
            continue
        cita = db.get(Cita, row.cita_id)
        if cita is None:
            continue
        consultorio = db.get(Consultorio, cita.consultorio_id)
        row.consultorio = consultorio_label(consultorio)
        row.texto_visible = render_turno_text(db, cita)


def medico_reference_count(db: Session, medico_id: UUID) -> int:
    counts = [
        select(func.count()).select_from(MedicoPaciente).where(MedicoPaciente.medico_id == medico_id),
        select(func.count()).select_from(Cita).where(Cita.medico_id == medico_id),
        select(func.count()).select_from(UsuarioRol).where(UsuarioRol.medico_id == medico_id),
        select(func.count()).select_from(AsignacionMedicoConsultorio).where(AsignacionMedicoConsultorio.medico_id == medico_id),
        select(func.count()).select_from(AsignacionOperador).where(AsignacionOperador.medico_id == medico_id),
    ]
    return sum(int(db.execute(query).scalar_one()) for query in counts)


def candidate_medicos_for_user(db: Session, user: Usuario, today: date) -> list[Medico]:
    role_medico_ids = set(
        db.execute(
            select(UsuarioRol.medico_id)
            .join(Role, Role.id == UsuarioRol.rol_id)
            .where(
                UsuarioRol.usuario_id == user.id,
                UsuarioRol.activo.is_(True),
                UsuarioRol.fecha_inicio <= today,
                or_(UsuarioRol.fecha_fin.is_(None), UsuarioRol.fecha_fin >= today),
                UsuarioRol.medico_id.is_not(None),
                Role.codigo == "MEDICO",
                Role.activo.is_(True),
            )
        ).scalars()
    )
    candidates_by_id: dict[UUID, Medico] = {}
    for medico in db.execute(select(Medico).where(Medico.usuario_id == user.id)).scalars():
        candidates_by_id[medico.id] = medico
    if role_medico_ids:
        for medico in db.execute(select(Medico).where(Medico.id.in_(role_medico_ids))).scalars():
            candidates_by_id[medico.id] = medico

    user_identities = user_identity_values(user)
    unlinked = db.execute(select(Medico).where(Medico.usuario_id.is_(None), Medico.activo.is_(True))).scalars()
    for medico in unlinked:
        if user_identities & medico_identity_values(medico):
            candidates_by_id[medico.id] = medico

    return list(candidates_by_id.values())


def choose_canonical_medico(db: Session, candidates: list[Medico]) -> Medico | None:
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda medico: (
            medico_reference_count(db, medico.id),
            bool(medico.usuario_id),
            bool(medico.activo),
            medico.updated_at,
        ),
    )


def merge_medico_into(db: Session, source: Medico, target: Medico) -> set[UUID]:
    if source.id == target.id:
        return set()
    affected_cita_ids = set(db.execute(select(Cita.id).where(Cita.medico_id == source.id)).scalars())

    paciente_rows = list(db.execute(select(MedicoPaciente).where(MedicoPaciente.medico_id == source.id)).scalars())
    for row in paciente_rows:
        target_row = db.get(MedicoPaciente, {"medico_id": target.id, "paciente_id": row.paciente_id})
        if target_row is not None:
            target_row.activo = target_row.activo or row.activo
            db.delete(row)
        else:
            row.medico_id = target.id

    db.execute(update(Cita).where(Cita.medico_id == source.id).values(medico_id=target.id))
    db.execute(update(UsuarioRol).where(UsuarioRol.medico_id == source.id).values(medico_id=target.id))
    db.execute(update(AsignacionMedicoConsultorio).where(AsignacionMedicoConsultorio.medico_id == source.id).values(medico_id=target.id))
    db.execute(update(AsignacionOperador).where(AsignacionOperador.medico_id == source.id).values(medico_id=target.id))
    if target.plantilla_turno == TURNO_TEMPLATE_DEFAULT and source.plantilla_turno != TURNO_TEMPLATE_DEFAULT:
        target.plantilla_turno = source.plantilla_turno
    source.usuario_id = None
    source.activo = False
    return affected_cita_ids


def sync_medicos_for_medico_users(db: Session, today: date | None = None, user_id: UUID | None = None) -> bool:
    effective_today = today or date.today()
    users_query = (
        select(Usuario)
        .join(UsuarioRol, UsuarioRol.usuario_id == Usuario.id)
        .join(Role, Role.id == UsuarioRol.rol_id)
        .where(
            Role.codigo == "MEDICO",
            Role.activo.is_(True),
            UsuarioRol.activo.is_(True),
            UsuarioRol.fecha_inicio <= effective_today,
            or_(UsuarioRol.fecha_fin.is_(None), UsuarioRol.fecha_fin >= effective_today),
            func.upper(Usuario.estado) == "ACTIVO",
        )
        .distinct()
    )
    if user_id is not None:
        users_query = users_query.where(Usuario.id == user_id)

    changed = False
    for user in db.execute(users_query).scalars().unique():
        candidates = candidate_medicos_for_user(db, user, effective_today)
        medico = choose_canonical_medico(db, candidates)
        if medico is None:
            medico = Medico(usuario_id=user.id, nombre=user.nombre, apellidos=user.apellidos, activo=True)
            db.add(medico)
            changed = True
            db.flush()
            continue
        affected_cita_ids = set(db.execute(select(Cita.id).where(Cita.medico_id == medico.id)).scalars())
        for duplicate in candidates:
            if duplicate.id == medico.id:
                continue
            affected_cita_ids.update(merge_medico_into(db, duplicate, medico))
            changed = True
        if medico.usuario_id != user.id:
            medico.usuario_id = user.id
            changed = True
        if medico.nombre != user.nombre:
            medico.nombre = user.nombre
            changed = True
        if medico.apellidos != user.apellidos:
            medico.apellidos = user.apellidos
            changed = True
        if medico.nombre_visible is not None:
            medico.nombre_visible = None
            changed = True
        if not medico.activo:
            medico.activo = True
            changed = True
        if affected_cita_ids:
            refresh_turnos_for_citas(db, affected_cita_ids)

    if changed:
        db.flush()
    return changed
