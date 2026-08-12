from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select, true
from sqlalchemy.orm import Session

from app.models.complejo import Complejo
from app.models.display import TurnoDisplay
from app.models.flow import Cita, MedicoPaciente, Paciente
from app.models.operational import (
    AsignacionMedicoConsultorio,
    AsignacionOperador,
    Consultorio,
    Medico,
    Operador,
    Piso,
    Role,
    UsuarioRol,
)
from app.models.usuario import Usuario


def _today(today: date | None) -> date:
    return today or date.today()


def _active_role_scope_conditions(user: Usuario, today: date | None = None) -> list[Any]:
    effective_today = _today(today)
    return [
        UsuarioRol.usuario_id == user.id,
        UsuarioRol.activo.is_(True),
        UsuarioRol.fecha_inicio <= effective_today,
        or_(UsuarioRol.fecha_fin.is_(None), UsuarioRol.fecha_fin >= effective_today),
        Role.activo.is_(True),
    ]


def _active_operator_scope_conditions(user: Usuario, today: date | None = None) -> list[Any]:
    effective_today = _today(today)
    return [
        Operador.usuario_id == user.id,
        Operador.activo.is_(True),
        AsignacionOperador.activo.is_(True),
        AsignacionOperador.fecha_inicio <= effective_today,
        or_(AsignacionOperador.fecha_fin.is_(None), AsignacionOperador.fecha_fin >= effective_today),
    ]


def user_has_global_access(db: Session, user: Usuario, today: date | None = None) -> bool:
    return (
        db.execute(
            select(Role.id)
            .join(UsuarioRol, UsuarioRol.rol_id == Role.id)
            .where(*_active_role_scope_conditions(user, today), Role.codigo == "ADMIN_SISTEMA")
            .limit(1)
        ).first()
        is not None
    )


def _role_scope_exists(user: Usuario, predicate: Any, today: date | None = None) -> Any:
    return (
        select(UsuarioRol.id)
        .join(Role, UsuarioRol.rol_id == Role.id)
        .where(*_active_role_scope_conditions(user, today), predicate)
        .exists()
    )


def _operator_scope_exists(user: Usuario, predicate: Any, today: date | None = None) -> Any:
    return (
        select(AsignacionOperador.id)
        .join(Operador, Operador.id == AsignacionOperador.operador_id)
        .where(*_active_operator_scope_conditions(user, today), predicate)
        .exists()
    )


def _location_access_predicate(
    user: Usuario,
    consultorio_id_col: Any,
    piso_id_col: Any,
    complejo_id_col: Any,
    today: date | None = None,
) -> Any:
    role_location = _role_scope_exists(
        user,
        or_(
            UsuarioRol.consultorio_id == consultorio_id_col,
            UsuarioRol.piso_id == piso_id_col,
            and_(
                UsuarioRol.torre_id.is_not(None),
                select(Piso.id)
                .where(Piso.id == piso_id_col, Piso.torre_id == UsuarioRol.torre_id)
                .exists(),
            ),
            UsuarioRol.complejo_id == complejo_id_col,
            and_(
                UsuarioRol.institucion_id.is_not(None),
                select(Complejo.id)
                .where(Complejo.id == complejo_id_col, Complejo.institucion_id == UsuarioRol.institucion_id)
                .exists(),
            ),
        ),
        today,
    )
    operator_location = _operator_scope_exists(
        user,
        AsignacionOperador.consultorio_id == consultorio_id_col,
        today,
    )
    return or_(role_location, operator_location)


def _medico_access_predicate(user: Usuario, medico_id_col: Any, today: date | None = None) -> Any:
    own_medico = (
        select(Medico.id)
        .where(Medico.id == medico_id_col, Medico.usuario_id == user.id, Medico.activo.is_(True))
        .exists()
    )
    role_medico = _role_scope_exists(user, UsuarioRol.medico_id == medico_id_col, today)
    operator_medico = _operator_scope_exists(user, AsignacionOperador.medico_id == medico_id_col, today)
    return or_(own_medico, role_medico, operator_medico)


def _active_medico_consultorio_conditions(today: date | None = None) -> list[Any]:
    effective_today = _today(today)
    return [
        AsignacionMedicoConsultorio.activo.is_(True),
        AsignacionMedicoConsultorio.fecha_inicio <= effective_today,
        or_(
            AsignacionMedicoConsultorio.fecha_fin.is_(None),
            AsignacionMedicoConsultorio.fecha_fin >= effective_today,
        ),
    ]


def _medico_via_location_access_predicate(user: Usuario, medico_id_col: Any, today: date | None = None) -> Any:
    return (
        select(AsignacionMedicoConsultorio.id)
        .join(Consultorio, Consultorio.id == AsignacionMedicoConsultorio.consultorio_id)
        .where(
            AsignacionMedicoConsultorio.medico_id == medico_id_col,
            *_active_medico_consultorio_conditions(today),
            _location_access_predicate(user, Consultorio.id, Consultorio.piso_id, Consultorio.complejo_id, today),
        )
        .exists()
    )


def medico_catalog_access_predicate(db: Session, user: Usuario, today: date | None = None) -> Any:
    if user_has_global_access(db, user, today):
        return true()
    return or_(
        _medico_access_predicate(user, Medico.id, today),
        _medico_via_location_access_predicate(user, Medico.id, today),
    )


def consultorio_catalog_access_predicate(db: Session, user: Usuario, today: date | None = None) -> Any:
    if user_has_global_access(db, user, today):
        return true()
    consultorio_by_location = _location_access_predicate(
        user,
        Consultorio.id,
        Consultorio.piso_id,
        Consultorio.complejo_id,
        today,
    )
    consultorio_by_medico = (
        select(AsignacionMedicoConsultorio.id)
        .where(
            AsignacionMedicoConsultorio.consultorio_id == Consultorio.id,
            *_active_medico_consultorio_conditions(today),
            _medico_access_predicate(user, AsignacionMedicoConsultorio.medico_id, today),
        )
        .exists()
    )
    return or_(consultorio_by_location, consultorio_by_medico)


def piso_catalog_access_predicate(db: Session, user: Usuario, today: date | None = None) -> Any:
    if user_has_global_access(db, user, today):
        return true()
    return (
        select(Consultorio.id)
        .where(
            Consultorio.piso_id == Piso.id,
            Consultorio.activo.is_(True),
            consultorio_catalog_access_predicate(db, user, today),
        )
        .exists()
    )


def cita_access_predicate(db: Session, user: Usuario, today: date | None = None) -> Any:
    if user_has_global_access(db, user, today):
        return true()
    return or_(
        _location_access_predicate(user, Cita.consultorio_id, Cita.piso_id, Cita.complejo_id, today),
        _medico_access_predicate(user, Cita.medico_id, today),
    )


def paciente_access_predicate(db: Session, user: Usuario, today: date | None = None) -> Any:
    if user_has_global_access(db, user, today):
        return true()
    paciente_by_medico = (
        select(MedicoPaciente.paciente_id)
        .where(
            MedicoPaciente.paciente_id == Paciente.id,
            MedicoPaciente.activo.is_(True),
            _medico_access_predicate(user, MedicoPaciente.medico_id, today),
        )
        .exists()
    )
    paciente_by_cita = (
        select(Cita.id)
        .where(
            Cita.paciente_id == Paciente.id,
            cita_access_predicate(db, user, today),
        )
        .exists()
    )
    return or_(paciente_by_medico, paciente_by_cita)


def turno_display_access_predicate(db: Session, user: Usuario, today: date | None = None) -> Any:
    if user_has_global_access(db, user, today):
        return true()
    turno_by_location = _location_access_predicate(
        user,
        TurnoDisplay.consultorio_id,
        TurnoDisplay.piso_id,
        TurnoDisplay.complejo_id,
        today,
    )
    turno_by_cita_medico = (
        select(Cita.id)
        .where(
            Cita.id == TurnoDisplay.cita_id,
            _medico_access_predicate(user, Cita.medico_id, today),
        )
        .exists()
    )
    return or_(turno_by_location, turno_by_cita_medico)


def can_access_cita(db: Session, user: Usuario, cita_id: Any, today: date | None = None) -> bool:
    return (
        db.execute(
            select(Cita.id)
            .where(Cita.id == cita_id, cita_access_predicate(db, user, today))
            .limit(1)
        ).first()
        is not None
    )


def can_access_paciente(db: Session, user: Usuario, paciente_id: Any, today: date | None = None) -> bool:
    return (
        db.execute(
            select(Paciente.id)
            .where(Paciente.id == paciente_id, paciente_access_predicate(db, user, today))
            .limit(1)
        ).first()
        is not None
    )


def can_access_medico(db: Session, user: Usuario, medico_id: Any, today: date | None = None) -> bool:
    if user_has_global_access(db, user, today):
        return True
    own_medico = (
        db.execute(
            select(Medico.id)
            .where(Medico.id == medico_id, Medico.usuario_id == user.id, Medico.activo.is_(True))
            .limit(1)
        ).first()
        is not None
    )
    if own_medico:
        return True
    role_medico = (
        db.execute(
            select(UsuarioRol.id)
            .join(Role, UsuarioRol.rol_id == Role.id)
            .where(*_active_role_scope_conditions(user, today), UsuarioRol.medico_id == medico_id)
            .limit(1)
        ).first()
        is not None
    )
    if role_medico:
        return True
    return (
        db.execute(
            select(AsignacionOperador.id)
            .join(Operador, Operador.id == AsignacionOperador.operador_id)
            .where(*_active_operator_scope_conditions(user, today), AsignacionOperador.medico_id == medico_id)
            .limit(1)
        ).first()
        is not None
    )


def can_assign_patient_to_medico(db: Session, user: Usuario, medico_id: Any, today: date | None = None) -> bool:
    if can_access_medico(db, user, medico_id, today):
        return True
    if user_has_global_access(db, user, today):
        return True
    return (
        db.execute(
            select(AsignacionMedicoConsultorio.id)
            .join(Consultorio, Consultorio.id == AsignacionMedicoConsultorio.consultorio_id)
            .where(
                AsignacionMedicoConsultorio.medico_id == medico_id,
                AsignacionMedicoConsultorio.activo.is_(True),
                AsignacionMedicoConsultorio.fecha_inicio <= _today(today),
                or_(
                    AsignacionMedicoConsultorio.fecha_fin.is_(None),
                    AsignacionMedicoConsultorio.fecha_fin >= _today(today),
                ),
                _location_access_predicate(user, Consultorio.id, Consultorio.piso_id, Consultorio.complejo_id, today),
            )
            .limit(1)
        ).first()
        is not None
    )


def cita_payload_is_accessible(db: Session, user: Usuario, payload: dict[str, Any], today: date | None = None) -> bool:
    if user_has_global_access(db, user, today):
        return True
    consultorio_id = payload.get("consultorio_id")
    medico_id = payload.get("medico_id")
    if medico_id is not None and can_access_medico(db, user, medico_id, today):
        return True
    if consultorio_id is None:
        return False
    consultorio = db.get(Consultorio, consultorio_id)
    if consultorio is None:
        return False
    return (
        db.execute(
            select(Consultorio.id)
            .where(
                Consultorio.id == consultorio.id,
                _location_access_predicate(user, Consultorio.id, Consultorio.piso_id, Consultorio.complejo_id, today),
            )
            .limit(1)
        ).first()
        is not None
    )


def ensure_cita_access(db: Session, user: Usuario, cita_id: Any, today: date | None = None) -> None:
    if not can_access_cita(db, user, cita_id, today):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada.")


def ensure_paciente_access(db: Session, user: Usuario, paciente_id: Any, today: date | None = None) -> None:
    if not can_access_paciente(db, user, paciente_id, today):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado.")


def ensure_medico_patient_assignment_access(db: Session, user: Usuario, medico_id: Any, today: date | None = None) -> None:
    if not can_assign_patient_to_medico(db, user, medico_id, today):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Médico no encontrado.")
