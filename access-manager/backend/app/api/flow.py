from __future__ import annotations

from datetime import date, datetime, time
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.core.database import get_db
from app.core.security import require_permission, require_role
from app.models.complejo import Complejo
from app.models.display import PantallaTurnos, PantallaTurnosCluster
from app.models.flow import Cita, EventoLlegada, MedicoPaciente, Paciente, QrToken
from app.models.institucion import Institucion
from app.models.operational import (
    AsignacionMedicoConsultorio,
    Consultorio,
    ConsultorioCluster,
    Medico,
    Piso,
    Role,
    SalaEspera,
    Torre,
    UsuarioRol,
)
from app.models.usuario import Usuario
from app.schemas.complejo import ComplejoRead
from app.schemas.flow import (
    CheckinRequest,
    CheckinResponse,
    CitaActionResponse,
    CitaCreate,
    CitaListItem,
    CitaRead,
    CitaSearchResult,
    CitaUpdate,
    MobileSessionResponse,
    PacienteCreate,
    PacienteRead,
    PacienteUpdate,
    QrCheckinRequest,
    QrGenerateResponse,
    QrRead,
    QrValidarRequest,
    QrValidarResponse,
    TicketResponse,
)
from app.schemas.institucion import InstitucionRead
from app.schemas.operational import ConsultorioRead, MedicoRead, PisoRead, TorreRead
from app.services.audit_service import audit_safe_dict, record_audit_event
from app.services.access_scope import (
    cita_agenda_access_predicate,
    cita_access_predicate,
    cita_payload_is_accessible,
    complejo_catalog_access_predicate,
    consultorio_catalog_access_predicate,
    ensure_cita_access,
    ensure_medico_patient_assignment_access,
    ensure_paciente_access,
    institucion_catalog_access_predicate,
    medico_catalog_access_predicate,
    paciente_access_predicate,
    piso_catalog_access_predicate,
    torre_catalog_access_predicate,
)
from app.services.medico_sync import sync_medicos_for_medico_users
from app.services.checkin_service import checkin_window_status
from app.services.folio_service import generate_patient_folio, generate_turn_folio
from app.services.qr_service import cancel_qr, encode_qr_payload, generate_qr, now_utc, token_digest, validate_qr

pacientes_router = APIRouter()
citas_router = APIRouter()
qr_router = APIRouter()
mobile_router = APIRouter()
catalogos_operativos_router = APIRouter()

ADMIN_ROLE_CODES = {"ADMIN_SISTEMA", "ADMIN_NEGOCIO"}
ASSISTANT_MEDICO_ROLE_CODES = {"ASISTENTE_MEDICO", "ASISTENTE", "RECEPCIONISTA"}

CatalogosOperativosUser = Depends(require_permission("pacientes", "citas", "citas-hoy", "turnos-llamados"))
PacientesReadUser = Depends(require_permission("pacientes"))
PacientesWriteUser = Depends(require_permission("pacientes", minimum="editar"))
CitasAgendaReadUser = Depends(require_permission("citas"))
CitasAgendaWriteUser = Depends(require_permission("citas", minimum="editar"))
CitasTodayReadUser = Depends(require_permission("citas-hoy"))
CitasOperationalReadUser = Depends(require_permission("citas", "citas-hoy"))
CitasOperationalWriteUser = Depends(require_permission("citas", "citas-hoy", minimum="editar"))
MobileSessionUser = Depends(require_role("RECEPCIONISTA", "ADMIN_NEGOCIO"))
MobileCheckinUser = Depends(require_role("RECEPCIONISTA"))


def business_today() -> date:
    return datetime.now(ZoneInfo("America/Mexico_City")).date()


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def exists_or_404(db: Session, model: type, item_id: UUID, label: str) -> object:
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} no encontrado.")
    return item


def normalize_search(value: str) -> str:
    return f"%{value.strip().lower()}%"


def normalized_digits(value: str | None) -> str | None:
    if value is None:
        return None
    digits = "".join(char for char in value if char.isdigit())
    return digits or None


def active_role_codes(db: Session, usuario: Usuario) -> set[str]:
    today = business_today()
    return set(
        db.execute(
            select(Role.codigo)
            .join(UsuarioRol, UsuarioRol.rol_id == Role.id)
            .where(
                UsuarioRol.usuario_id == usuario.id,
                UsuarioRol.activo.is_(True),
                UsuarioRol.fecha_inicio <= today,
                or_(UsuarioRol.fecha_fin.is_(None), UsuarioRol.fecha_fin >= today),
                Role.activo.is_(True),
            )
        ).scalars()
    )


def active_user_role_conditions(usuario: Usuario, today: date) -> list[Any]:
    return [
        UsuarioRol.usuario_id == usuario.id,
        UsuarioRol.activo.is_(True),
        UsuarioRol.fecha_inicio <= today,
        or_(UsuarioRol.fecha_fin.is_(None), UsuarioRol.fecha_fin >= today),
        Role.activo.is_(True),
    ]


def user_has_direct_medico_assignments(db: Session, usuario: Usuario, today: date) -> bool:
    return (
        db.execute(
            select(UsuarioRol.id)
            .join(Role, Role.id == UsuarioRol.rol_id)
            .where(*active_user_role_conditions(usuario, today), UsuarioRol.medico_id.is_not(None))
            .limit(1)
        ).first()
        is not None
    )


def medico_assigned_to_user_predicate(usuario: Usuario, today: date, role_codes: set[str] | None = None):
    conditions = [
        *active_user_role_conditions(usuario, today),
        UsuarioRol.medico_id == Medico.id,
    ]
    if role_codes is not None:
        conditions.append(Role.codigo.in_(role_codes))
    return select(UsuarioRol.id).join(Role, Role.id == UsuarioRol.rol_id).where(*conditions).exists()


def patient_full_name(paciente: Paciente | None) -> str | None:
    if paciente is None:
        return None
    parts = [paciente.nombre, paciente.apellido_paterno, paciente.apellido_materno]
    text = " ".join(part for part in parts if part)
    return text or None


def patient_display_name(paciente: Paciente | None) -> str | None:
    if paciente is None:
        return None
    return paciente.nombre_preferido or patient_full_name(paciente)


def patient_medical_name(paciente: Paciente | None) -> str | None:
    if paciente is None:
        return None
    full_name = patient_full_name(paciente)
    if paciente.nombre_preferido and full_name:
        return f"{paciente.nombre_preferido} ({full_name})"
    return paciente.nombre_preferido or full_name


def consultorio_label(consultorio: Consultorio | None) -> str | None:
    if consultorio is None:
        return None
    return consultorio.nombre_visible or consultorio.codigo


def piso_label(piso: Piso | None) -> str | None:
    if piso is None:
        return None
    return piso.nombre_visible or f"Piso {piso.numero}"


def torre_label(torre: Torre | None) -> str | None:
    if torre is None:
        return None
    return torre.nombre


def medico_label(medico: Medico | None) -> str | None:
    if medico is None:
        return None
    return medico.nombre_visible or f"{medico.nombre} {medico.apellidos}"


def consultorio_catalog_read(db: Session, consultorio: Consultorio) -> ConsultorioRead:
    cluster_ids = list(
        db.execute(
            select(ConsultorioCluster.cluster_id).where(ConsultorioCluster.consultorio_id == consultorio.id)
        ).scalars()
    )
    return ConsultorioRead(
        id=consultorio.id,
        complejo_id=consultorio.complejo_id,
        piso_id=consultorio.piso_id,
        codigo=consultorio.codigo,
        nombre_visible=consultorio.nombre_visible,
        instrucciones_acceso=consultorio.instrucciones_acceso,
        notas=consultorio.notas,
        cluster_ids=cluster_ids,
        activo=consultorio.activo,
        created_at=consultorio.created_at,
        updated_at=consultorio.updated_at,
    )


def ensure_medico_catalog_access(db: Session, current_user: Usuario, medico_id: UUID) -> None:
    query = (
        select(Medico.id)
        .where(
            Medico.id == medico_id,
            Medico.activo.is_(True),
            medico_catalog_access_predicate(db, current_user, business_today()),
        )
        .limit(1)
    )
    if db.execute(query).first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Médico no encontrado.")


def active_medico_assignment_conditions(medico_id: UUID) -> list[Any]:
    today = business_today()
    return [
        AsignacionMedicoConsultorio.medico_id == medico_id,
        AsignacionMedicoConsultorio.activo.is_(True),
        AsignacionMedicoConsultorio.fecha_inicio <= today,
        or_(
            AsignacionMedicoConsultorio.fecha_fin.is_(None),
            AsignacionMedicoConsultorio.fecha_fin >= today,
        ),
    ]


def active_medico_role_consultorio_conditions(medico_id: UUID) -> list[Any]:
    today = business_today()
    medico_user_id = select(Medico.usuario_id).where(Medico.id == medico_id).scalar_subquery()
    return [
        Role.codigo == "MEDICO",
        Role.activo.is_(True),
        UsuarioRol.activo.is_(True),
        UsuarioRol.fecha_inicio <= today,
        or_(UsuarioRol.fecha_fin.is_(None), UsuarioRol.fecha_fin >= today),
        UsuarioRol.consultorio_id.is_not(None),
        or_(UsuarioRol.medico_id == medico_id, UsuarioRol.usuario_id == medico_user_id),
    ]


def consultorio_role_assigned_to_medico(medico_id: UUID):
    return (
        select(UsuarioRol.id)
        .join(Role, Role.id == UsuarioRol.rol_id)
        .where(
            UsuarioRol.consultorio_id == Consultorio.id,
            *active_medico_role_consultorio_conditions(medico_id),
        )
        .exists()
    )


def piso_role_assigned_to_medico(medico_id: UUID):
    role_consultorio = aliased(Consultorio)
    return (
        select(UsuarioRol.id)
        .join(Role, Role.id == UsuarioRol.rol_id)
        .join(role_consultorio, role_consultorio.id == UsuarioRol.consultorio_id)
        .where(
            role_consultorio.activo.is_(True),
            role_consultorio.piso_id == Piso.id,
            *active_medico_role_consultorio_conditions(medico_id),
        )
        .exists()
    )


def torre_role_assigned_to_medico(medico_id: UUID):
    role_consultorio = aliased(Consultorio)
    role_piso = aliased(Piso)
    return (
        select(UsuarioRol.id)
        .join(Role, Role.id == UsuarioRol.rol_id)
        .join(role_consultorio, role_consultorio.id == UsuarioRol.consultorio_id)
        .join(role_piso, role_piso.id == role_consultorio.piso_id)
        .where(
            role_consultorio.activo.is_(True),
            role_piso.activo.is_(True),
            role_piso.torre_id == Torre.id,
            *active_medico_role_consultorio_conditions(medico_id),
        )
        .exists()
    )


def complejo_role_assigned_to_medico(medico_id: UUID):
    role_consultorio = aliased(Consultorio)
    return (
        select(UsuarioRol.id)
        .join(Role, Role.id == UsuarioRol.rol_id)
        .join(role_consultorio, role_consultorio.id == UsuarioRol.consultorio_id)
        .where(
            role_consultorio.activo.is_(True),
            role_consultorio.complejo_id == Complejo.id,
            *active_medico_role_consultorio_conditions(medico_id),
        )
        .exists()
    )


def institucion_role_assigned_to_medico(medico_id: UUID):
    role_consultorio = aliased(Consultorio)
    role_complejo = aliased(Complejo)
    return (
        select(UsuarioRol.id)
        .join(Role, Role.id == UsuarioRol.rol_id)
        .join(role_consultorio, role_consultorio.id == UsuarioRol.consultorio_id)
        .join(role_complejo, role_complejo.id == role_consultorio.complejo_id)
        .where(
            role_consultorio.activo.is_(True),
            role_complejo.activo.is_(True),
            role_complejo.institucion_id == Institucion.id,
            *active_medico_role_consultorio_conditions(medico_id),
        )
        .exists()
    )


def consultorio_assigned_to_medico(medico_id: UUID):
    return or_(
        select(AsignacionMedicoConsultorio.id)
        .where(
            AsignacionMedicoConsultorio.consultorio_id == Consultorio.id,
            *active_medico_assignment_conditions(medico_id),
        )
        .exists(),
        consultorio_role_assigned_to_medico(medico_id),
    )


def piso_assigned_to_medico(medico_id: UUID):
    return or_(
        select(AsignacionMedicoConsultorio.id)
        .join(Consultorio, Consultorio.id == AsignacionMedicoConsultorio.consultorio_id)
        .where(Consultorio.piso_id == Piso.id, *active_medico_assignment_conditions(medico_id))
        .exists(),
        piso_role_assigned_to_medico(medico_id),
    )


def torre_assigned_to_medico(medico_id: UUID):
    return or_(
        select(AsignacionMedicoConsultorio.id)
        .join(Consultorio, Consultorio.id == AsignacionMedicoConsultorio.consultorio_id)
        .join(Piso, Piso.id == Consultorio.piso_id)
        .where(Piso.torre_id == Torre.id, *active_medico_assignment_conditions(medico_id))
        .exists(),
        torre_role_assigned_to_medico(medico_id),
    )


def complejo_assigned_to_medico(medico_id: UUID):
    return or_(
        select(AsignacionMedicoConsultorio.id)
        .join(Consultorio, Consultorio.id == AsignacionMedicoConsultorio.consultorio_id)
        .where(Consultorio.complejo_id == Complejo.id, *active_medico_assignment_conditions(medico_id))
        .exists(),
        complejo_role_assigned_to_medico(medico_id),
    )


def institucion_assigned_to_medico(medico_id: UUID):
    return or_(
        select(AsignacionMedicoConsultorio.id)
        .join(Consultorio, Consultorio.id == AsignacionMedicoConsultorio.consultorio_id)
        .join(Complejo, Complejo.id == Consultorio.complejo_id)
        .where(Complejo.institucion_id == Institucion.id, *active_medico_assignment_conditions(medico_id))
        .exists(),
        institucion_role_assigned_to_medico(medico_id),
    )


@catalogos_operativos_router.get("/medicos", response_model=list[MedicoRead])
def list_medicos_operativos(
    db: Session = Depends(get_db),
    current_user: Usuario = CatalogosOperativosUser,
) -> list[Medico]:
    today = business_today()
    if sync_medicos_for_medico_users(db, today):
        db.commit()
    roles = active_role_codes(db, current_user)
    access_predicate = medico_catalog_access_predicate(db, current_user, today)
    if not roles.intersection(ADMIN_ROLE_CODES):
        if "MEDICO" in roles:
            access_predicate = or_(
                Medico.usuario_id == current_user.id,
                medico_assigned_to_user_predicate(current_user, today, {"MEDICO"}),
            )
        elif roles.intersection(ASSISTANT_MEDICO_ROLE_CODES) or user_has_direct_medico_assignments(db, current_user, today):
            access_predicate = medico_assigned_to_user_predicate(current_user, today)
    query = (
        select(Medico)
        .where(Medico.activo.is_(True), access_predicate)
        .order_by(
            func.lower(func.coalesce(Medico.apellidos, "")),
            func.lower(func.coalesce(Medico.nombre, "")),
            Medico.id,
        )
    )
    return list(db.execute(query).scalars())


@catalogos_operativos_router.get("/instituciones", response_model=list[InstitucionRead])
def list_instituciones_operativas(
    medico_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = CatalogosOperativosUser,
) -> list[Institucion]:
    if medico_id is not None:
        ensure_medico_catalog_access(db, current_user, medico_id)
    query = (
        select(Institucion)
        .where(
            Institucion.activo.is_(True),
            institucion_assigned_to_medico(medico_id)
            if medico_id is not None
            else institucion_catalog_access_predicate(db, current_user, business_today()),
        )
        .order_by(func.lower(Institucion.nombre), Institucion.id)
    )
    return list(db.execute(query).scalars())


@catalogos_operativos_router.get("/complejos", response_model=list[ComplejoRead])
def list_complejos_operativos(
    medico_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = CatalogosOperativosUser,
) -> list[Complejo]:
    if medico_id is not None:
        ensure_medico_catalog_access(db, current_user, medico_id)
    query = (
        select(Complejo)
        .where(
            Complejo.activo.is_(True),
            complejo_assigned_to_medico(medico_id)
            if medico_id is not None
            else complejo_catalog_access_predicate(db, current_user, business_today()),
        )
        .order_by(func.lower(Complejo.nombre), Complejo.id)
    )
    return list(db.execute(query).scalars())


@catalogos_operativos_router.get("/torres", response_model=list[TorreRead])
def list_torres_operativas(
    medico_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = CatalogosOperativosUser,
) -> list[Torre]:
    if medico_id is not None:
        ensure_medico_catalog_access(db, current_user, medico_id)
    query = (
        select(Torre)
        .where(
            Torre.activo.is_(True),
            torre_assigned_to_medico(medico_id)
            if medico_id is not None
            else torre_catalog_access_predicate(db, current_user, business_today()),
        )
        .order_by(Torre.complejo_id, func.lower(Torre.nombre), Torre.id)
    )
    return list(db.execute(query).scalars())


@catalogos_operativos_router.get("/consultorios", response_model=list[ConsultorioRead])
def list_consultorios_operativos(
    medico_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = CatalogosOperativosUser,
) -> list[ConsultorioRead]:
    if medico_id is not None:
        ensure_medico_catalog_access(db, current_user, medico_id)
    query = (
        select(Consultorio)
        .where(
            Consultorio.activo.is_(True),
            consultorio_assigned_to_medico(medico_id)
            if medico_id is not None
            else consultorio_catalog_access_predicate(db, current_user, business_today()),
        )
        .order_by(
            Consultorio.complejo_id,
            Consultorio.piso_id,
            func.lower(func.coalesce(Consultorio.nombre_visible, Consultorio.codigo)),
            func.lower(Consultorio.codigo),
            Consultorio.id,
        )
    )
    return [consultorio_catalog_read(db, item) for item in db.execute(query).scalars()]


@catalogos_operativos_router.get("/pisos", response_model=list[PisoRead])
def list_pisos_operativos(
    medico_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = CatalogosOperativosUser,
) -> list[Piso]:
    if medico_id is not None:
        ensure_medico_catalog_access(db, current_user, medico_id)
    query = (
        select(Piso)
        .where(
            Piso.activo.is_(True),
            piso_assigned_to_medico(medico_id)
            if medico_id is not None
            else piso_catalog_access_predicate(db, current_user, business_today()),
        )
        .order_by(
            Piso.complejo_id,
            func.lower(func.coalesce(Piso.codigo, "")),
            Piso.numero,
            func.lower(func.coalesce(Piso.nombre_visible, "")),
            Piso.id,
        )
    )
    return list(db.execute(query).scalars())


def medico_ids_for_paciente(db: Session, paciente_id: UUID) -> list[UUID]:
    return list(
        db.execute(
            select(MedicoPaciente.medico_id)
            .where(
                MedicoPaciente.paciente_id == paciente_id,
                MedicoPaciente.activo.is_(True),
            )
            .order_by(MedicoPaciente.created_at)
        ).scalars()
    )


def paciente_read(db: Session, paciente: Paciente) -> PacienteRead:
    return PacienteRead.model_validate(paciente).model_copy(
        update={"medico_ids": medico_ids_for_paciente(db, paciente.id)}
    )


def paciente_belongs_to_medico(db: Session, paciente_id: UUID, medico_id: UUID) -> bool:
    return (
        db.execute(
            select(MedicoPaciente)
            .where(
                MedicoPaciente.paciente_id == paciente_id,
                MedicoPaciente.medico_id == medico_id,
                MedicoPaciente.activo.is_(True),
            )
            .limit(1)
        ).scalar_one_or_none()
        is not None
    )


def paciente_for_medico_or_404(db: Session, paciente_id: UUID, medico_id: UUID) -> Paciente:
    item = exists_or_404(db, Paciente, paciente_id, "Paciente")
    exists_or_404(db, Medico, medico_id, "Médico")
    if not paciente_belongs_to_medico(db, paciente_id, medico_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado para el médico indicado.",
        )
    return item


def assign_paciente_to_medico(db: Session, paciente_id: UUID, medico_id: UUID) -> None:
    exists_or_404(db, Medico, medico_id, "Médico")
    row = db.get(MedicoPaciente, {"medico_id": medico_id, "paciente_id": paciente_id})
    if row is None:
        db.add(MedicoPaciente(medico_id=medico_id, paciente_id=paciente_id))
    else:
        row.activo = True


def pacientes_for_medico_query(medico_id: UUID):
    return (
        select(Paciente)
        .join(MedicoPaciente, MedicoPaciente.paciente_id == Paciente.id)
        .where(
            MedicoPaciente.medico_id == medico_id,
            MedicoPaciente.activo.is_(True),
        )
    )


def patient_order_columns():
    return (
        func.lower(func.coalesce(Paciente.apellido_paterno, "")),
        func.lower(func.coalesce(Paciente.apellido_materno, "")),
        func.lower(func.coalesce(Paciente.nombre, "")),
        func.lower(func.coalesce(Paciente.nombre_preferido, "")),
        Paciente.folio_paciente,
    )


def cita_zona_horaria(db: Session, cita: Cita) -> str:
    complejo = db.get(Complejo, cita.complejo_id)
    return complejo.zona_horaria if complejo is not None else "UTC"


def cita_item(db: Session, cita: Cita) -> CitaListItem:
    payload = CitaRead.model_validate(cita).model_dump()
    paciente = db.get(Paciente, cita.paciente_id)
    return CitaListItem(
        **payload,
        paciente=patient_display_name(paciente),
        paciente_nombre_completo=patient_medical_name(paciente),
        consultorio=consultorio_label(db.get(Consultorio, cita.consultorio_id)),
        piso=piso_label(db.get(Piso, cita.piso_id)),
        medico=medico_label(db.get(Medico, cita.medico_id)),
    )


def cita_search_item(db: Session, cita: Cita) -> CitaSearchResult:
    return CitaSearchResult(
        id=cita.id,
        folio_turno=cita.folio_turno,
        hora_cita=cita.hora_cita,
        consultorio=consultorio_label(db.get(Consultorio, cita.consultorio_id)),
        piso=piso_label(db.get(Piso, cita.piso_id)),
        estado=cita.estado,
    )


def unique_citas(rows) -> list[Cita]:
    seen: set[UUID] = set()
    result: list[Cita] = []
    for row in rows:
        if row.id in seen:
            continue
        seen.add(row.id)
        result.append(row)
    return result


def validate_patient_contact(paciente: Paciente) -> None:
    if not paciente.celular and paciente.fecha_nacimiento is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Debe indicar celular o fecha de nacimiento.",
        )


def validate_patient_identity(paciente: Paciente) -> None:
    if not paciente.nombre_preferido and not (paciente.nombre and paciente.apellido_paterno):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Debe indicar nombre preferido o nombre y apellido paterno.",
        )


def active_display_exists_for_clusters(db: Session, cluster_ids: list[UUID]) -> bool:
    cluster_ids = list(dict.fromkeys(cluster_ids))
    if not cluster_ids:
        return False
    if (
        db.execute(
            select(PantallaTurnos.id)
            .join(PantallaTurnosCluster, PantallaTurnosCluster.pantalla_id == PantallaTurnos.id)
            .where(PantallaTurnos.activa.is_(True), PantallaTurnosCluster.cluster_id.in_(cluster_ids))
            .limit(1)
        ).first()
        is not None
    ):
        return True
    screen_has_bridge = (
        select(PantallaTurnosCluster.pantalla_id)
        .where(PantallaTurnosCluster.pantalla_id == PantallaTurnos.id)
        .exists()
    )
    return (
        db.execute(
            select(PantallaTurnos.id)
            .where(
                PantallaTurnos.activa.is_(True),
                PantallaTurnos.cluster_espera_id.in_(cluster_ids),
                ~screen_has_bridge,
            )
            .limit(1)
        ).first()
        is not None
    )


def consultorio_has_display_coverage(db: Session, consultorio_id: UUID) -> bool:
    cluster_ids = list(
        db.execute(select(ConsultorioCluster.cluster_id).where(ConsultorioCluster.consultorio_id == consultorio_id)).scalars()
    )
    return active_display_exists_for_clusters(db, cluster_ids)


def validate_cita_scope(db: Session, data: dict, item: Cita | None = None) -> None:
    paciente_id = data.get("paciente_id", getattr(item, "paciente_id", None))
    medico_id = data.get("medico_id", getattr(item, "medico_id", None))
    consultorio_id = data.get("consultorio_id", getattr(item, "consultorio_id", None))
    complejo_id = data.get("complejo_id", getattr(item, "complejo_id", None))
    piso_id = data.get("piso_id", getattr(item, "piso_id", None))
    sala_prevista_id = data.get("sala_prevista_id", getattr(item, "sala_prevista_id", None))

    if paciente_id is not None:
        exists_or_404(db, Paciente, paciente_id, "Paciente")
    if medico_id is not None:
        exists_or_404(db, Medico, medico_id, "Médico")
    if paciente_id is not None and medico_id is not None and not paciente_belongs_to_medico(db, paciente_id, medico_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El paciente no está asignado al médico indicado.",
        )
    if complejo_id is not None:
        exists_or_404(db, Complejo, complejo_id, "Campus")
    if piso_id is not None:
        piso = exists_or_404(db, Piso, piso_id, "Piso")
        if complejo_id is not None and piso.complejo_id != complejo_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El piso no pertenece al campus indicado.")
    if consultorio_id is not None:
        consultorio = exists_or_404(db, Consultorio, consultorio_id, "Consultorio")
        if complejo_id is not None and consultorio.complejo_id != complejo_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El consultorio no pertenece al campus indicado.")
        if piso_id is not None and consultorio.piso_id != piso_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El consultorio no pertenece al piso indicado.")
        if not consultorio_has_display_coverage(db, consultorio.id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El consultorio debe estar asociado a por lo menos un clúster con una pantalla de turnos activa.",
            )
    if sala_prevista_id is not None:
        sala = exists_or_404(db, SalaEspera, sala_prevista_id, "Sala de espera")
        if complejo_id is not None and sala.complejo_id != complejo_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La sala no pertenece al campus indicado.")
        if piso_id is not None and sala.piso_id != piso_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La sala no pertenece al piso indicado.")


def duplicate_warnings(db: Session, data: dict, exclude_id: UUID | None = None) -> list[dict[str, str]]:
    paciente = db.get(Paciente, data["paciente_id"])
    if paciente is None:
        return []
    query = select(Cita).join(Paciente, Cita.paciente_id == Paciente.id).where(
        Cita.fecha_cita == data["fecha_cita"],
        Cita.medico_id == data["medico_id"],
        Cita.estado.notin_(("CANCELADA", "EXPIRADA")),
    )
    if paciente.nombre_preferido:
        query = query.where(func.lower(func.coalesce(Paciente.nombre_preferido, "")) == paciente.nombre_preferido.lower())
    elif paciente.nombre and paciente.apellido_paterno:
        query = query.where(
            func.lower(func.coalesce(Paciente.nombre, "")) == paciente.nombre.lower(),
            func.lower(func.coalesce(Paciente.apellido_paterno, "")) == paciente.apellido_paterno.lower(),
        )
    else:
        return []
    if not paciente.nombre_preferido and paciente.apellido_materno:
        query = query.where(func.lower(Paciente.apellido_materno) == paciente.apellido_materno.lower())
    if paciente.celular:
        query = query.where(Paciente.celular == paciente.celular)
    elif paciente.fecha_nacimiento:
        query = query.where(Paciente.fecha_nacimiento == paciente.fecha_nacimiento)
    else:
        return []
    if exclude_id is not None:
        query = query.where(Cita.id != exclude_id)
    return [
        {"cita_id": str(cita.id), "folio_turno": cita.folio_turno, "estado": cita.estado}
        for cita in db.execute(query.limit(5)).scalars()
    ]


def query_citas(
    db: Session,
    fecha: date | None = None,
    fecha_inicio: date | None = None,
    hora_inicio: time | None = None,
    hora_fin: time | None = None,
    institucion_id: UUID | None = None,
    complejo_id: UUID | None = None,
    torre_id: UUID | None = None,
    piso_id: UUID | None = None,
    consultorio_id: UUID | None = None,
    medico_id: UUID | None = None,
    paciente: str | None = None,
    celular: str | None = None,
    fecha_nacimiento: date | None = None,
    estado: str | None = None,
    tipo: str | None = None,
):
    query = select(Cita)
    patient_joined = False
    if paciente:
        patient_joined = True
        full_name = func.lower(
            func.coalesce(Paciente.nombre, "")
            + " "
            + func.coalesce(Paciente.apellido_paterno, "")
            + " "
            + func.coalesce(Paciente.apellido_materno, "")
            + " "
            + func.coalesce(Paciente.nombre_preferido, "")
        )
        query = query.join(Paciente, Cita.paciente_id == Paciente.id)
        for term_text in paciente.split():
            term = normalize_search(term_text)
            query = query.where(
                or_(
                    full_name.like(term),
                    func.lower(Paciente.celular).like(term),
                    func.lower(Paciente.folio_paciente).like(term),
                )
            )
    if celular:
        if not patient_joined:
            query = query.join(Paciente, Cita.paciente_id == Paciente.id)
            patient_joined = True
        digits = normalized_digits(celular)
        if digits:
            celular_digits = func.replace(
                func.replace(
                    func.replace(func.replace(func.replace(func.coalesce(Paciente.celular, ""), " ", ""), "-", ""), "(", ""),
                    ")",
                    "",
                ),
                "+",
                "",
            )
            query = query.where(celular_digits.like(f"%{digits}%"))
    if fecha_nacimiento is not None:
        if not patient_joined:
            query = query.join(Paciente, Cita.paciente_id == Paciente.id)
        query = query.where(Paciente.fecha_nacimiento == fecha_nacimiento)
    if fecha is not None:
        query = query.where(Cita.fecha_cita == fecha)
        if hora_inicio is not None:
            query = query.where(Cita.hora_cita >= hora_inicio)
        if hora_fin is not None:
            query = query.where(Cita.hora_cita <= hora_fin)
    elif fecha_inicio is not None:
        if hora_inicio is not None:
            query = query.where(
                or_(
                    Cita.fecha_cita > fecha_inicio,
                    and_(Cita.fecha_cita == fecha_inicio, Cita.hora_cita >= hora_inicio),
                )
            )
        else:
            query = query.where(Cita.fecha_cita >= fecha_inicio)
        if hora_fin is not None:
            query = query.where(Cita.hora_cita <= hora_fin)
    elif hora_inicio is not None:
        query = query.where(Cita.hora_cita >= hora_inicio)
        if hora_fin is not None:
            query = query.where(Cita.hora_cita <= hora_fin)
    elif hora_fin is not None:
        query = query.where(Cita.hora_cita <= hora_fin)
    if institucion_id is not None:
        query = query.where(
            select(Complejo.id)
            .where(
                Complejo.id == Cita.complejo_id,
                Complejo.institucion_id == institucion_id,
            )
            .exists()
        )
    if complejo_id is not None:
        query = query.where(Cita.complejo_id == complejo_id)
    if torre_id is not None:
        query = query.where(
            select(Piso.id)
            .where(
                Piso.id == Cita.piso_id,
                Piso.torre_id == torre_id,
            )
            .exists()
        )
    if piso_id is not None:
        query = query.where(Cita.piso_id == piso_id)
    if consultorio_id is not None:
        query = query.where(Cita.consultorio_id == consultorio_id)
    if medico_id is not None:
        query = query.where(Cita.medico_id == medico_id)
    if estado is not None:
        query = query.where(Cita.estado == estado)
    if tipo is not None:
        query = query.where(Cita.tipo == tipo)
    return query.order_by(Cita.fecha_cita, Cita.hora_cita, Cita.folio_turno)


def get_active_qr_payload(db: Session, cita: Cita) -> tuple[QrToken, str]:
    timestamp = now_utc()
    qr_token = db.execute(
        select(QrToken).where(
            QrToken.cita_id == cita.id,
            QrToken.estado == "GENERADO",
            QrToken.fecha_expiracion > timestamp,
        ).order_by(QrToken.fecha_emision.desc())
    ).scalar_one_or_none()
    if qr_token is not None:
        token = encode_qr_payload(cita, qr_token.fecha_emision, qr_token.fecha_expiracion)
        if token_digest(token) == qr_token.token_hash:
            return qr_token, token
    return generate_qr(db, cita)


def create_arrival_event(
    db: Session,
    cita: Cita,
    tipo: str,
    canal: str,
    request: Request,
    sala_id: UUID | None = None,
    usuario_id: UUID | None = None,
    dispositivo_id: str | None = None,
) -> EventoLlegada:
    timestamp = now_utc()
    event = EventoLlegada(
        cita_id=cita.id,
        tipo=tipo,
        sala_id=sala_id,
        canal=canal,
        usuario_id=usuario_id,
        dispositivo_id=dispositivo_id,
        ip_origen=client_ip(request),
        created_at=timestamp,
    )
    db.add(event)
    if tipo == "CHECKIN_LOBBY":
        cita.estado = "LLEGO_LOBBY"
    db.flush()
    return event


@pacientes_router.get("/buscar", response_model=list[PacienteRead])
def buscar_pacientes(
    q: str = Query(min_length=1),
    medico_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = PacientesReadUser,
) -> list[PacienteRead]:
    query = select(Paciente).where(paciente_access_predicate(db, current_user, business_today()))
    if medico_id is not None:
        ensure_medico_patient_assignment_access(db, current_user, medico_id, business_today())
        query = query.join(MedicoPaciente, MedicoPaciente.paciente_id == Paciente.id).where(
            MedicoPaciente.medico_id == medico_id,
            MedicoPaciente.activo.is_(True),
        )
    term = normalize_search(q)
    rows = list(
        db.execute(
            query
            .where(
                or_(
                    func.lower(func.coalesce(Paciente.nombre, "")).like(term),
                    func.lower(func.coalesce(Paciente.nombre_preferido, "")).like(term),
                    func.lower(func.coalesce(Paciente.apellido_paterno, "")).like(term),
                    func.lower(func.coalesce(Paciente.apellido_materno, "")).like(term),
                    func.lower(func.coalesce(Paciente.celular, "")).like(term),
                    func.lower(Paciente.folio_paciente).like(term),
                )
            )
            .order_by(*patient_order_columns())
            .limit(50)
        ).scalars()
    )
    return [paciente_read(db, row) for row in rows]


@pacientes_router.get("", response_model=list[PacienteRead])
def list_pacientes(
    medico_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = PacientesReadUser,
) -> list[PacienteRead]:
    query = select(Paciente).where(paciente_access_predicate(db, current_user, business_today()))
    if medico_id is not None:
        ensure_medico_patient_assignment_access(db, current_user, medico_id, business_today())
        query = query.join(MedicoPaciente, MedicoPaciente.paciente_id == Paciente.id).where(
            MedicoPaciente.medico_id == medico_id,
            MedicoPaciente.activo.is_(True),
        )
    rows = list(
        db.execute(
            query
            .order_by(*patient_order_columns())
            .limit(200)
        ).scalars()
    )
    return [paciente_read(db, row) for row in rows]


@pacientes_router.get("/{paciente_id}", response_model=PacienteRead)
def get_paciente(
    paciente_id: UUID,
    medico_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = PacientesReadUser,
) -> PacienteRead:
    if medico_id is not None:
        paciente = paciente_for_medico_or_404(db, paciente_id, medico_id)
    else:
        paciente = exists_or_404(db, Paciente, paciente_id, "Paciente")
    ensure_paciente_access(db, current_user, paciente.id, business_today())
    return paciente_read(db, paciente)


@pacientes_router.post("", response_model=PacienteRead, status_code=status.HTTP_201_CREATED)
def create_paciente(
    payload: PacienteCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = PacientesWriteUser,
) -> PacienteRead:
    data = payload.model_dump()
    medico_id = data.pop("medico_id")
    ensure_medico_patient_assignment_access(db, current_user, medico_id, business_today())
    item = Paciente(**data, folio_paciente=generate_patient_folio(db))
    db.add(item)
    db.flush()
    assign_paciente_to_medico(db, item.id, medico_id)
    db.flush()
    record_audit_event(
        db,
        evento="PACIENTE_CREADO",
        entidad="pacientes",
        entidad_id=item.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_despues={**audit_safe_dict(item), "medico_ids": [str(medico_id)]},
    )
    db.commit()
    db.refresh(item)
    return paciente_read(db, item)


@pacientes_router.put("/{paciente_id}", response_model=PacienteRead)
def update_paciente(
    paciente_id: UUID,
    payload: PacienteUpdate,
    request: Request,
    medico_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: Usuario = PacientesWriteUser,
) -> PacienteRead:
    item = paciente_for_medico_or_404(db, paciente_id, medico_id)
    ensure_paciente_access(db, current_user, item.id, business_today())
    before = audit_safe_dict(item)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    validate_patient_identity(item)
    validate_patient_contact(item)
    db.flush()
    record_audit_event(
        db,
        evento="PACIENTE_EDITADO",
        entidad="pacientes",
        entidad_id=item.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_antes=before,
        valor_despues=audit_safe_dict(item),
    )
    db.commit()
    db.refresh(item)
    return paciente_read(db, item)


@pacientes_router.patch("/{paciente_id}/activar", response_model=PacienteRead)
def activar_paciente(
    paciente_id: UUID,
    request: Request,
    medico_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: Usuario = PacientesWriteUser,
) -> PacienteRead:
    return set_paciente_active(paciente_id, medico_id, True, request, db, current_user)


@pacientes_router.patch("/{paciente_id}/desactivar", response_model=PacienteRead)
def desactivar_paciente(
    paciente_id: UUID,
    request: Request,
    medico_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: Usuario = PacientesWriteUser,
) -> PacienteRead:
    return set_paciente_active(paciente_id, medico_id, False, request, db, current_user)


def set_paciente_active(
    paciente_id: UUID,
    medico_id: UUID,
    active: bool,
    request: Request,
    db: Session,
    current_user: Usuario,
) -> PacienteRead:
    item = paciente_for_medico_or_404(db, paciente_id, medico_id)
    ensure_paciente_access(db, current_user, item.id, business_today())
    before = audit_safe_dict(item)
    item.activo = active
    item.desactivado_en = None if active else now_utc()
    db.flush()
    record_audit_event(
        db,
        evento="PACIENTE_EDITADO",
        entidad="pacientes",
        entidad_id=item.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_antes=before,
        valor_despues=audit_safe_dict(item),
    )
    db.commit()
    db.refresh(item)
    return paciente_read(db, item)


@pacientes_router.patch("/{paciente_id}/marcar-borrado", response_model=PacienteRead)
def marcar_paciente_borrado(
    paciente_id: UUID,
    request: Request,
    medico_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: Usuario = PacientesWriteUser,
) -> PacienteRead:
    item = paciente_for_medico_or_404(db, paciente_id, medico_id)
    ensure_paciente_access(db, current_user, item.id, business_today())
    before = audit_safe_dict(item)
    item.marcado_borrado_en = now_utc()
    db.flush()
    record_audit_event(
        db,
        evento="PACIENTE_MARCADO_BORRADO",
        entidad="pacientes",
        entidad_id=item.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_antes=before,
        valor_despues=audit_safe_dict(item),
    )
    db.commit()
    db.refresh(item)
    return paciente_read(db, item)


@citas_router.get("/hoy", response_model=list[CitaListItem])
def citas_hoy(
    fecha: date | None = None,
    hora_inicio: time | None = None,
    hora_fin: time | None = None,
    institucion_id: UUID | None = None,
    complejo_id: UUID | None = None,
    torre_id: UUID | None = None,
    piso_id: UUID | None = None,
    consultorio_id: UUID | None = None,
    medico_id: UUID | None = None,
    paciente: str | None = None,
    estado: str | None = None,
    tipo: str | None = None,
    db: Session = Depends(get_db),
    current_user: Usuario = CitasTodayReadUser,
) -> list[CitaListItem]:
    query = query_citas(
        db,
        fecha=fecha or business_today(),
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        institucion_id=institucion_id,
        complejo_id=complejo_id,
        torre_id=torre_id,
        piso_id=piso_id,
        consultorio_id=consultorio_id,
        medico_id=medico_id,
        paciente=paciente,
        estado=estado,
        tipo=tipo,
    )
    rows = db.execute(query.where(cita_access_predicate(db, current_user, business_today()))).scalars()
    return [cita_item(db, row) for row in rows]


@citas_router.get("/buscar", response_model=list[CitaSearchResult])
def buscar_citas(
    paciente: str = Query(min_length=1),
    fecha: date | None = None,
    fecha_inicio: date | None = None,
    hora_inicio: time | None = None,
    hora_fin: time | None = None,
    institucion_id: UUID | None = None,
    complejo_id: UUID | None = None,
    torre_id: UUID | None = None,
    piso_id: UUID | None = None,
    consultorio_id: UUID | None = None,
    medico_id: UUID | None = None,
    celular: str | None = None,
    fecha_nacimiento: date | None = None,
    estado: str | None = None,
    tipo: str | None = None,
    db: Session = Depends(get_db),
    current_user: Usuario = CitasOperationalReadUser,
) -> list[CitaSearchResult]:
    rows = db.execute(
        query_citas(
            db,
            fecha=fecha if fecha is not None else (None if fecha_inicio is not None else business_today()),
            fecha_inicio=fecha_inicio,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            institucion_id=institucion_id,
            complejo_id=complejo_id,
            torre_id=torre_id,
            piso_id=piso_id,
            consultorio_id=consultorio_id,
            medico_id=medico_id,
            paciente=paciente,
            celular=celular,
            fecha_nacimiento=fecha_nacimiento,
            estado=estado,
            tipo=tipo,
        )
        .where(cita_access_predicate(db, current_user, business_today()))
        .limit(20)
    ).scalars()
    return [cita_search_item(db, row) for row in rows]


@citas_router.get("", response_model=list[CitaListItem])
def list_citas(
    fecha: date | None = None,
    fecha_inicio: date | None = None,
    hora_inicio: time | None = None,
    hora_fin: time | None = None,
    institucion_id: UUID | None = None,
    complejo_id: UUID | None = None,
    torre_id: UUID | None = None,
    piso_id: UUID | None = None,
    consultorio_id: UUID | None = None,
    medico_id: UUID | None = None,
    paciente: str | None = None,
    estado: str | None = None,
    tipo: str | None = None,
    db: Session = Depends(get_db),
    current_user: Usuario = CitasAgendaReadUser,
) -> list[CitaListItem]:
    query = query_citas(
        db,
        fecha=fecha,
        fecha_inicio=fecha_inicio,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        institucion_id=institucion_id,
        complejo_id=complejo_id,
        torre_id=torre_id,
        piso_id=piso_id,
        consultorio_id=consultorio_id,
        medico_id=medico_id,
        paciente=paciente,
        estado=estado,
        tipo=tipo,
    )
    rows = db.execute(query.where(cita_agenda_access_predicate(db, current_user, business_today())).limit(200)).scalars()
    return [cita_item(db, row) for row in unique_citas(rows)]


@citas_router.post("/exportacion", status_code=status.HTTP_201_CREATED)
def registrar_exportacion_citas(
    request: Request,
    formato: str = Query(pattern="^(excel|csv|json)$"),
    fecha: date | None = None,
    fecha_inicio: date | None = None,
    hora_inicio: time | None = None,
    hora_fin: time | None = None,
    institucion_id: UUID | None = None,
    complejo_id: UUID | None = None,
    torre_id: UUID | None = None,
    piso_id: UUID | None = None,
    consultorio_id: UUID | None = None,
    medico_id: UUID | None = None,
    paciente: str | None = None,
    estado: str | None = None,
    tipo: str | None = None,
    db: Session = Depends(get_db),
    current_user: Usuario = CitasOperationalReadUser,
) -> dict[str, bool]:
    record_audit_event(
        db,
        evento="CITAS_EXPORTADAS",
        entidad="citas",
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_despues={
            "formato": formato,
            "fecha": str(fecha or business_today()),
            "fecha_inicio": str(fecha_inicio) if fecha_inicio else None,
            "hora_inicio": hora_inicio.strftime("%H:%M") if hora_inicio else None,
            "hora_fin": hora_fin.strftime("%H:%M") if hora_fin else None,
            "institucion_id": str(institucion_id) if institucion_id else None,
            "complejo_id": str(complejo_id) if complejo_id else None,
            "torre_id": str(torre_id) if torre_id else None,
            "piso_id": str(piso_id) if piso_id else None,
            "consultorio_id": str(consultorio_id) if consultorio_id else None,
            "medico_id": str(medico_id) if medico_id else None,
            "paciente": paciente,
            "estado": estado,
            "tipo": tipo,
        },
    )
    db.commit()
    return {"ok": True}


@citas_router.get("/{cita_id}", response_model=CitaListItem)
def get_cita(cita_id: UUID, db: Session = Depends(get_db), current_user: Usuario = CitasOperationalReadUser) -> CitaListItem:
    ensure_cita_access(db, current_user, cita_id, business_today())
    return cita_item(db, exists_or_404(db, Cita, cita_id, "Cita"))


@citas_router.post("", response_model=CitaRead, status_code=status.HTTP_201_CREATED)
def create_cita(
    payload: CitaCreate,
    request: Request,
    confirmar_duplicado: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: Usuario = CitasAgendaWriteUser,
) -> Cita:
    data = payload.model_dump()
    validate_cita_scope(db, data)
    if not cita_payload_is_accessible(db, current_user, data, business_today()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene alcance para crear esta cita.")
    warnings = duplicate_warnings(db, data)
    if warnings and not confirmar_duplicado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"mensaje": "Existe una posible cita duplicada. Confirme para crearla.", "duplicados": warnings},
        )
    item = Cita(**data, folio_turno=generate_turn_folio(db, payload.complejo_id, payload.fecha_cita), creada_por=current_user.id)
    db.add(item)
    db.flush()
    record_audit_event(
        db,
        evento="CITA_CREADA",
        entidad="citas",
        entidad_id=item.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_despues=audit_safe_dict(item),
    )
    db.commit()
    db.refresh(item)
    return item


@citas_router.put("/{cita_id}", response_model=CitaRead)
def update_cita(
    cita_id: UUID,
    payload: CitaUpdate,
    request: Request,
    confirmar_duplicado: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: Usuario = CitasAgendaWriteUser,
) -> Cita:
    item = exists_or_404(db, Cita, cita_id, "Cita")
    ensure_cita_access(db, current_user, item.id, business_today())
    before = audit_safe_dict(item)
    data = payload.model_dump(exclude_unset=True)
    merged = {
        "paciente_id": data.get("paciente_id", item.paciente_id),
        "medico_id": data.get("medico_id", item.medico_id),
        "consultorio_id": data.get("consultorio_id", item.consultorio_id),
        "complejo_id": data.get("complejo_id", item.complejo_id),
        "piso_id": data.get("piso_id", item.piso_id),
        "sala_prevista_id": data.get("sala_prevista_id", item.sala_prevista_id),
        "fecha_cita": data.get("fecha_cita", item.fecha_cita),
        "hora_cita": data.get("hora_cita", item.hora_cita),
    }
    validate_cita_scope(db, merged, item)
    if not cita_payload_is_accessible(db, current_user, merged, business_today()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene alcance para actualizar esta cita.")
    warnings = duplicate_warnings(db, merged, exclude_id=item.id)
    if warnings and not confirmar_duplicado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"mensaje": "Existe una posible cita duplicada. Confirme para actualizarla.", "duplicados": warnings},
        )
    regenerate_folio = "complejo_id" in data or "fecha_cita" in data
    for key, value in data.items():
        setattr(item, key, value)
    if regenerate_folio:
        item.folio_turno = generate_turn_folio(db, item.complejo_id, item.fecha_cita)
    db.flush()
    record_audit_event(
        db,
        evento="CITA_EDITADA",
        entidad="citas",
        entidad_id=item.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_antes=before,
        valor_despues=audit_safe_dict(item),
    )
    db.commit()
    db.refresh(item)
    return item


def set_cita_state(cita_id: UUID, state: str, event_name: str, request: Request, db: Session, current_user: Usuario) -> CitaActionResponse:
    item = exists_or_404(db, Cita, cita_id, "Cita")
    ensure_cita_access(db, current_user, item.id, business_today())
    before = audit_safe_dict(item)
    item.estado = state
    db.flush()
    record_audit_event(
        db,
        evento=event_name,
        entidad="citas",
        entidad_id=item.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_antes=before,
        valor_despues=audit_safe_dict(item),
    )
    db.commit()
    db.refresh(item)
    return CitaActionResponse(id=item.id, estado=item.estado, folio_turno=item.folio_turno)


@citas_router.patch("/{cita_id}/cancelar", response_model=CitaActionResponse)
def cancelar_cita(cita_id: UUID, request: Request, db: Session = Depends(get_db), current_user: Usuario = CitasOperationalWriteUser):
    ensure_cita_access(db, current_user, cita_id, business_today())
    cancel_qr(db, cita_id)
    return set_cita_state(cita_id, "CANCELADA", "CITA_CANCELADA", request, db, current_user)


@citas_router.patch("/{cita_id}/autorizar-pasar", response_model=CitaActionResponse)
def autorizar_pasar(cita_id: UUID, request: Request, db: Session = Depends(get_db), current_user: Usuario = CitasOperationalWriteUser):
    return set_cita_state(cita_id, "AUTORIZADO_PASAR", "ACCESO_AUTORIZADO", request, db, current_user)


@citas_router.patch("/{cita_id}/iniciar-consulta", response_model=CitaActionResponse)
def iniciar_consulta(cita_id: UUID, request: Request, db: Session = Depends(get_db), current_user: Usuario = CitasOperationalWriteUser):
    return set_cita_state(cita_id, "EN_CONSULTA", "CONSULTA_INICIADA", request, db, current_user)


@citas_router.patch("/{cita_id}/finalizar", response_model=CitaActionResponse)
def finalizar_consulta(cita_id: UUID, request: Request, db: Session = Depends(get_db), current_user: Usuario = CitasOperationalWriteUser):
    return set_cita_state(cita_id, "FINALIZADA", "CONSULTA_FINALIZADA", request, db, current_user)


@citas_router.post("/{cita_id}/qr", response_model=QrGenerateResponse, status_code=status.HTTP_201_CREATED)
def generar_qr_cita(cita_id: UUID, request: Request, db: Session = Depends(get_db), current_user: Usuario = CitasOperationalWriteUser):
    cita = exists_or_404(db, Cita, cita_id, "Cita")
    ensure_cita_access(db, current_user, cita.id, business_today())
    qr_token, token = generate_qr(db, cita)
    record_audit_event(
        db,
        evento="QR_GENERADO",
        entidad="qr_tokens",
        entidad_id=qr_token.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_despues={"cita_id": str(cita.id), "estado": qr_token.estado, "fecha_expiracion": qr_token.fecha_expiracion.isoformat()},
    )
    db.commit()
    db.refresh(qr_token)
    return QrGenerateResponse(
        id=qr_token.id,
        cita_id=qr_token.cita_id,
        estado=qr_token.estado,
        fecha_emision=qr_token.fecha_emision,
        fecha_expiracion=qr_token.fecha_expiracion,
        qr_payload=token,
    )


@citas_router.get("/{cita_id}/qr", response_model=QrRead)
def get_qr_cita(cita_id: UUID, db: Session = Depends(get_db), current_user: Usuario = CitasOperationalReadUser):
    cita = exists_or_404(db, Cita, cita_id, "Cita")
    ensure_cita_access(db, current_user, cita.id, business_today())
    qr_token, _token = get_active_qr_payload(db, cita)
    db.commit()
    db.refresh(qr_token)
    return qr_token


@citas_router.patch("/{cita_id}/qr/cancelar", response_model=CitaActionResponse)
def cancelar_qr_cita(cita_id: UUID, request: Request, db: Session = Depends(get_db), current_user: Usuario = CitasOperationalWriteUser):
    cita = exists_or_404(db, Cita, cita_id, "Cita")
    ensure_cita_access(db, current_user, cita.id, business_today())
    cancel_qr(db, cita.id)
    record_audit_event(
        db,
        evento="QR_CANCELADO",
        entidad="citas",
        entidad_id=cita.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
    )
    db.commit()
    return CitaActionResponse(id=cita.id, estado=cita.estado, folio_turno=cita.folio_turno)


@citas_router.get("/{cita_id}/ticket", response_model=TicketResponse)
def get_ticket_cita(cita_id: UUID, db: Session = Depends(get_db), current_user: Usuario = CitasOperationalReadUser):
    cita = exists_or_404(db, Cita, cita_id, "Cita")
    ensure_cita_access(db, current_user, cita.id, business_today())
    return ticket_response_for_cita(db, cita)


def ticket_response_for_cita(db: Session, cita: Cita) -> TicketResponse:
    _qr_token, token = get_active_qr_payload(db, cita)
    db.commit()
    dias = ("LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO")
    consultorio = db.get(Consultorio, cita.consultorio_id)
    piso = db.get(Piso, cita.piso_id)
    torre = db.get(Torre, piso.torre_id) if piso is not None else None
    return TicketResponse(
        encabezado_fecha=f"{dias[cita.fecha_cita.weekday()]}-{cita.fecha_cita.day:02d}",
        leyenda="VÁLIDO SOLO HOY",
        turno=cita.folio_turno,
        qr_payload=token,
        consultorio=consultorio_label(consultorio) or "",
        torre=torre_label(torre) or "",
        piso=piso_label(piso) or "",
        hora=cita.hora_cita.strftime("%H:%M"),
    )


def authenticated_lobby_checkin(
    cita: Cita,
    payload: CheckinRequest,
    request: Request,
    db: Session,
    current_user: Usuario,
) -> CheckinResponse:
    if cita.estado in {"CANCELADA", "EXPIRADA", "NO_LLEGO"}:
        return CheckinResponse(
            resultado="ROJO",
            mensaje=f"La cita está en estado {cita.estado}.",
            cita_id=cita.id,
            folio_turno=cita.folio_turno,
            estado_cita=cita.estado,
        )
    resultado, mensaje = checkin_window_status(cita, zona_horaria=cita_zona_horaria(db, cita))
    if resultado != "ROJO":
        event = create_arrival_event(
            db,
            cita,
            "CHECKIN_LOBBY",
            payload.canal,
            request,
            payload.sala_id,
            current_user.id,
            payload.dispositivo_id,
        )
        record_audit_event(
            db,
            evento="CHECKIN_LOBBY",
            entidad="eventos_llegada",
            entidad_id=event.id,
            usuario_id=current_user.id,
            canal=payload.canal,
            ip_origen=client_ip(request),
            valor_despues={"cita_id": str(cita.id), "resultado": resultado},
        )
        db.commit()
        db.refresh(cita)
    return CheckinResponse(resultado=resultado, mensaje=mensaje, cita_id=cita.id, folio_turno=cita.folio_turno, estado_cita=cita.estado)


@mobile_router.get("/session", response_model=MobileSessionResponse)
def mobile_session(db: Session = Depends(get_db), current_user: Usuario = MobileSessionUser) -> MobileSessionResponse:
    roles = active_role_codes(db, current_user)
    return MobileSessionResponse(
        usuario_id=current_user.id,
        nombre=current_user.nombre,
        email=current_user.email,
        roles=sorted(roles),
        can_checkin=bool(roles.intersection({"ADMIN_SISTEMA", "RECEPCIONISTA"})),
        can_view_logs=bool(roles.intersection({"ADMIN_SISTEMA", "ADMIN_NEGOCIO"})),
    )


@mobile_router.get("/citas/buscar", response_model=list[CitaSearchResult])
def mobile_buscar_citas(
    paciente: str = Query(min_length=1),
    celular: str | None = None,
    fecha_nacimiento: date | None = None,
    fecha: date | None = None,
    db: Session = Depends(get_db),
    current_user: Usuario = MobileCheckinUser,
) -> list[CitaSearchResult]:
    if not normalized_digits(celular) and fecha_nacimiento is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Indique celular o fecha de nacimiento para buscar la cita.",
        )
    query = query_citas(
        db,
        fecha=fecha or business_today(),
        paciente=paciente,
        celular=celular,
        fecha_nacimiento=fecha_nacimiento,
    )
    rows = db.execute(query.where(cita_access_predicate(db, current_user, business_today())).limit(20)).scalars()
    return [cita_search_item(db, row) for row in rows]


@mobile_router.get("/citas/{cita_id}/ticket", response_model=TicketResponse)
def mobile_ticket_cita(cita_id: UUID, db: Session = Depends(get_db), current_user: Usuario = MobileCheckinUser) -> TicketResponse:
    cita = exists_or_404(db, Cita, cita_id, "Cita")
    ensure_cita_access(db, current_user, cita.id, business_today())
    return ticket_response_for_cita(db, cita)


@mobile_router.post("/citas/{cita_id}/checkin-lobby", response_model=CheckinResponse)
def mobile_checkin_lobby_cita(
    cita_id: UUID,
    payload: CheckinRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = MobileCheckinUser,
) -> CheckinResponse:
    cita = exists_or_404(db, Cita, cita_id, "Cita")
    ensure_cita_access(db, current_user, cita.id, business_today())
    return authenticated_lobby_checkin(cita, payload, request, db, current_user)


@mobile_router.post("/qr/checkin", response_model=CheckinResponse)
def mobile_checkin_qr(
    payload: QrCheckinRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = MobileCheckinUser,
) -> CheckinResponse:
    result = validate_qr(db, payload.token)
    if not result.valid or result.cita is None:
        record_audit_event(
            db,
            evento="QR_VALIDADO",
            entidad="qr_tokens",
            entidad_id=result.qr_token.id if result.qr_token else None,
            usuario_id=current_user.id,
            canal=payload.canal,
            ip_origen=client_ip(request),
            valor_despues={"valido": False, "resultado": result.status},
        )
        db.commit()
        return CheckinResponse(resultado="ROJO", mensaje=result.message)

    cita = result.cita
    resultado, mensaje = checkin_window_status(cita, zona_horaria=cita_zona_horaria(db, cita))
    if resultado != "ROJO":
        event = create_arrival_event(
            db,
            cita,
            "CHECKIN_LOBBY",
            payload.canal,
            request,
            payload.sala_id,
            current_user.id,
            payload.dispositivo_id,
        )
        if result.qr_token is not None:
            result.qr_token.estado = "USADO"
        record_audit_event(
            db,
            evento="CHECKIN_LOBBY",
            entidad="eventos_llegada",
            entidad_id=event.id,
            usuario_id=current_user.id,
            canal=payload.canal,
            ip_origen=client_ip(request),
            valor_despues={"cita_id": str(cita.id), "resultado": resultado},
        )
    record_audit_event(
        db,
        evento="QR_VALIDADO",
        entidad="qr_tokens",
        entidad_id=result.qr_token.id if result.qr_token else None,
        usuario_id=current_user.id,
        canal=payload.canal,
        ip_origen=client_ip(request),
        valor_despues={"valido": True, "resultado": resultado, "cita_id": str(cita.id)},
    )
    db.commit()
    db.refresh(cita)
    return CheckinResponse(resultado=resultado, mensaje=mensaje, cita_id=cita.id, folio_turno=cita.folio_turno, estado_cita=cita.estado)


@citas_router.post("/{cita_id}/checkin-lobby", response_model=CheckinResponse)
def checkin_lobby_cita(cita_id: UUID, payload: CheckinRequest, request: Request, db: Session = Depends(get_db)):
    cita = exists_or_404(db, Cita, cita_id, "Cita")
    if cita.estado in {"CANCELADA", "EXPIRADA", "NO_LLEGO"}:
        return CheckinResponse(resultado="ROJO", mensaje=f"La cita está en estado {cita.estado}.", cita_id=cita.id, folio_turno=cita.folio_turno, estado_cita=cita.estado)
    resultado, mensaje = checkin_window_status(cita, zona_horaria=cita_zona_horaria(db, cita))
    if resultado != "ROJO":
        event = create_arrival_event(db, cita, "CHECKIN_LOBBY", payload.canal, request, payload.sala_id, dispositivo_id=payload.dispositivo_id)
        record_audit_event(
            db,
            evento="CHECKIN_LOBBY",
            entidad="eventos_llegada",
            entidad_id=event.id,
            canal=payload.canal,
            ip_origen=client_ip(request),
            valor_despues={"cita_id": str(cita.id), "resultado": resultado},
        )
        db.commit()
        db.refresh(cita)
    return CheckinResponse(resultado=resultado, mensaje=mensaje, cita_id=cita.id, folio_turno=cita.folio_turno, estado_cita=cita.estado)


@citas_router.post("/{cita_id}/checkin-sala", response_model=CheckinResponse)
def checkin_sala_cita(cita_id: UUID, payload: CheckinRequest, request: Request, db: Session = Depends(get_db), current_user: Usuario = CitasOperationalWriteUser):
    cita = exists_or_404(db, Cita, cita_id, "Cita")
    ensure_cita_access(db, current_user, cita.id, business_today())
    event = create_arrival_event(db, cita, "CHECKIN_SALA", payload.canal, request, payload.sala_id, current_user.id, payload.dispositivo_id)
    record_audit_event(
        db,
        evento="CHECKIN_SALA",
        entidad="eventos_llegada",
        entidad_id=event.id,
        usuario_id=current_user.id,
        canal=payload.canal,
        ip_origen=client_ip(request),
        valor_despues={"cita_id": str(cita.id)},
    )
    db.commit()
    return CheckinResponse(resultado="VERDE", mensaje="Llegada a sala registrada.", cita_id=cita.id, folio_turno=cita.folio_turno, estado_cita=cita.estado)


@qr_router.post("/validar", response_model=QrValidarResponse)
def validar_qr(payload: QrValidarRequest, request: Request, db: Session = Depends(get_db)):
    result = validate_qr(db, payload.token)
    cita = result.cita
    record_audit_event(
        db,
        evento="QR_VALIDADO",
        entidad="qr_tokens",
        entidad_id=result.qr_token.id if result.qr_token else None,
        canal="API_EXTERNA",
        ip_origen=client_ip(request),
        valor_despues={"valido": result.valid, "resultado": result.status, "cita_id": str(cita.id) if cita else None},
    )
    db.commit()
    return QrValidarResponse(
        valido=result.valid,
        resultado=result.status,
        mensaje=result.message,
        cita_id=cita.id if cita else None,
        folio_turno=cita.folio_turno if cita else None,
        estado_cita=cita.estado if cita else None,
    )


@qr_router.post("/checkin", response_model=CheckinResponse)
def checkin_qr(payload: QrCheckinRequest, request: Request, db: Session = Depends(get_db)):
    result = validate_qr(db, payload.token)
    if not result.valid or result.cita is None:
        record_audit_event(
            db,
            evento="QR_VALIDADO",
            entidad="qr_tokens",
            entidad_id=result.qr_token.id if result.qr_token else None,
            canal=payload.canal,
            ip_origen=client_ip(request),
            valor_despues={"valido": False, "resultado": result.status},
        )
        db.commit()
        return CheckinResponse(resultado="ROJO", mensaje=result.message)

    cita = result.cita
    resultado, mensaje = checkin_window_status(cita, zona_horaria=cita_zona_horaria(db, cita))
    if resultado != "ROJO":
        event = create_arrival_event(db, cita, "CHECKIN_LOBBY", payload.canal, request, payload.sala_id, dispositivo_id=payload.dispositivo_id)
        if result.qr_token is not None:
            result.qr_token.estado = "USADO"
        record_audit_event(
            db,
            evento="CHECKIN_LOBBY",
            entidad="eventos_llegada",
            entidad_id=event.id,
            canal=payload.canal,
            ip_origen=client_ip(request),
            valor_despues={"cita_id": str(cita.id), "resultado": resultado},
        )
    record_audit_event(
        db,
        evento="QR_VALIDADO",
        entidad="qr_tokens",
        entidad_id=result.qr_token.id if result.qr_token else None,
        canal=payload.canal,
        ip_origen=client_ip(request),
        valor_despues={"valido": True, "resultado": resultado, "cita_id": str(cita.id)},
    )
    db.commit()
    db.refresh(cita)
    return CheckinResponse(resultado=resultado, mensaje=mensaje, cita_id=cita.id, folio_turno=cita.folio_turno, estado_cita=cita.estado)
