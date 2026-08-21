from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, not_, or_, select, true
from sqlalchemy.orm import Session, aliased

from app.models.complejo import Complejo
from app.models.display import PantallaTurnos, TurnoDisplay
from app.models.flow import Cita, MedicoPaciente, Paciente
from app.models.institucion import Institucion
from app.models.operational import (
    AsignacionMedicoConsultorio,
    AsignacionOperador,
    Consultorio,
    Medico,
    Operador,
    Piso,
    Role,
    Torre,
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


def _role_location_scope_condition() -> Any:
    return or_(
        UsuarioRol.institucion_id.is_not(None),
        UsuarioRol.complejo_id.is_not(None),
        UsuarioRol.torre_id.is_not(None),
        UsuarioRol.piso_id.is_not(None),
        UsuarioRol.consultorio_id.is_not(None),
        UsuarioRol.medico_id.is_not(None),
    )


def _role_global_location_scope_condition() -> Any:
    return and_(
        UsuarioRol.institucion_id.is_(None),
        UsuarioRol.complejo_id.is_(None),
        UsuarioRol.torre_id.is_(None),
        UsuarioRol.piso_id.is_(None),
        UsuarioRol.consultorio_id.is_(None),
        UsuarioRol.medico_id.is_(None),
        Role.codigo != "MEDICO",
    )


def _role_consultorio_scope_condition() -> Any:
    return UsuarioRol.consultorio_id.is_not(None)


def _role_piso_scope_condition() -> Any:
    return and_(UsuarioRol.consultorio_id.is_(None), UsuarioRol.piso_id.is_not(None))


def _role_torre_scope_condition() -> Any:
    return and_(
        UsuarioRol.consultorio_id.is_(None),
        UsuarioRol.piso_id.is_(None),
        UsuarioRol.torre_id.is_not(None),
    )


def _role_complejo_scope_condition() -> Any:
    return and_(
        UsuarioRol.consultorio_id.is_(None),
        UsuarioRol.piso_id.is_(None),
        UsuarioRol.torre_id.is_(None),
        UsuarioRol.complejo_id.is_not(None),
    )


def _role_institucion_scope_condition() -> Any:
    return and_(
        UsuarioRol.consultorio_id.is_(None),
        UsuarioRol.piso_id.is_(None),
        UsuarioRol.torre_id.is_(None),
        UsuarioRol.complejo_id.is_(None),
        UsuarioRol.institucion_id.is_not(None),
    )


def _unrestricted_location_access_predicate(user: Usuario, today: date | None = None) -> Any:
    active_role = _role_scope_exists(user, true(), today)
    global_location = _role_scope_exists(user, _role_global_location_scope_condition(), today)
    has_location_scope = _role_scope_exists(user, or_(_role_location_scope_condition(), Role.codigo == "MEDICO"), today)
    return and_(active_role, or_(global_location, not_(has_location_scope)))


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
            and_(_role_consultorio_scope_condition(), UsuarioRol.consultorio_id == consultorio_id_col),
            and_(_role_piso_scope_condition(), UsuarioRol.piso_id == piso_id_col),
            and_(
                _role_torre_scope_condition(),
                select(Piso.id)
                .where(Piso.id == piso_id_col, Piso.torre_id == UsuarioRol.torre_id)
                .correlate_except(Piso)
                .exists(),
            ),
            and_(_role_complejo_scope_condition(), UsuarioRol.complejo_id == complejo_id_col),
            and_(
                _role_institucion_scope_condition(),
                select(Complejo.id)
                .where(Complejo.id == complejo_id_col, Complejo.institucion_id == UsuarioRol.institucion_id)
                .correlate_except(Complejo)
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


def _piso_location_access_predicate(
    user: Usuario,
    piso_id_col: Any,
    torre_id_col: Any,
    complejo_id_col: Any,
    today: date | None = None,
) -> Any:
    role_location = _role_scope_exists(
        user,
        or_(
            and_(
                _role_consultorio_scope_condition(),
                select(Consultorio.id)
                .where(Consultorio.id == UsuarioRol.consultorio_id, Consultorio.piso_id == piso_id_col)
                .correlate_except(Consultorio)
                .exists(),
            ),
            and_(_role_piso_scope_condition(), UsuarioRol.piso_id == piso_id_col),
            and_(_role_torre_scope_condition(), UsuarioRol.torre_id == torre_id_col),
            and_(_role_complejo_scope_condition(), UsuarioRol.complejo_id == complejo_id_col),
            and_(
                _role_institucion_scope_condition(),
                select(Complejo.id)
                .where(Complejo.id == complejo_id_col, Complejo.institucion_id == UsuarioRol.institucion_id)
                .correlate_except(Complejo)
                .exists(),
            ),
        ),
        today,
    )
    operator_location = _operator_scope_exists(
        user,
        and_(
            AsignacionOperador.consultorio_id.is_not(None),
            select(Consultorio.id)
            .where(Consultorio.id == AsignacionOperador.consultorio_id, Consultorio.piso_id == piso_id_col)
            .correlate_except(Consultorio)
            .exists(),
        ),
        today,
    )
    return or_(role_location, operator_location)


def _torre_location_access_predicate(
    user: Usuario,
    torre_id_col: Any,
    complejo_id_col: Any,
    today: date | None = None,
) -> Any:
    role_location = _role_scope_exists(
        user,
        or_(
            and_(
                _role_consultorio_scope_condition(),
                select(Consultorio.id)
                .join(Piso, Piso.id == Consultorio.piso_id)
                .where(Consultorio.id == UsuarioRol.consultorio_id, Piso.torre_id == torre_id_col)
                .correlate_except(Consultorio, Piso)
                .exists(),
            ),
            and_(
                _role_piso_scope_condition(),
                select(Piso.id)
                .where(Piso.id == UsuarioRol.piso_id, Piso.torre_id == torre_id_col)
                .correlate_except(Piso)
                .exists(),
            ),
            and_(_role_torre_scope_condition(), UsuarioRol.torre_id == torre_id_col),
            and_(
                _role_complejo_scope_condition(),
                select(Torre.id)
                .where(Torre.id == torre_id_col, Torre.complejo_id == UsuarioRol.complejo_id)
                .correlate_except(Torre)
                .exists(),
            ),
            and_(
                _role_institucion_scope_condition(),
                select(Complejo.id)
                .where(Complejo.id == complejo_id_col, Complejo.institucion_id == UsuarioRol.institucion_id)
                .correlate_except(Complejo)
                .exists(),
            ),
        ),
        today,
    )
    operator_location = _operator_scope_exists(
        user,
        and_(
            AsignacionOperador.consultorio_id.is_not(None),
            select(Consultorio.id)
            .join(Piso, Piso.id == Consultorio.piso_id)
            .where(Consultorio.id == AsignacionOperador.consultorio_id, Piso.torre_id == torre_id_col)
            .correlate_except(Consultorio, Piso)
            .exists(),
        ),
        today,
    )
    return or_(role_location, operator_location)


def _complejo_location_access_predicate(
    user: Usuario,
    complejo_id_col: Any,
    institucion_id_col: Any,
    today: date | None = None,
) -> Any:
    role_location = _role_scope_exists(
        user,
        or_(
            and_(
                _role_consultorio_scope_condition(),
                select(Consultorio.id)
                .where(Consultorio.id == UsuarioRol.consultorio_id, Consultorio.complejo_id == complejo_id_col)
                .correlate_except(Consultorio)
                .exists(),
            ),
            and_(
                _role_piso_scope_condition(),
                select(Piso.id)
                .where(Piso.id == UsuarioRol.piso_id, Piso.complejo_id == complejo_id_col)
                .correlate_except(Piso)
                .exists(),
            ),
            and_(
                _role_torre_scope_condition(),
                select(Torre.id)
                .where(Torre.id == UsuarioRol.torre_id, Torre.complejo_id == complejo_id_col)
                .correlate_except(Torre)
                .exists(),
            ),
            and_(_role_complejo_scope_condition(), UsuarioRol.complejo_id == complejo_id_col),
            and_(_role_institucion_scope_condition(), UsuarioRol.institucion_id == institucion_id_col),
        ),
        today,
    )
    operator_location = _operator_scope_exists(
        user,
        or_(
            AsignacionOperador.complejo_id == complejo_id_col,
            and_(
                AsignacionOperador.consultorio_id.is_not(None),
                select(Consultorio.id)
                .where(Consultorio.id == AsignacionOperador.consultorio_id, Consultorio.complejo_id == complejo_id_col)
                .correlate_except(Consultorio)
                .exists(),
            ),
        ),
        today,
    )
    return or_(role_location, operator_location)


def _institucion_location_access_predicate(user: Usuario, institucion_id_col: Any, today: date | None = None) -> Any:
    role_location = _role_scope_exists(
        user,
        or_(
            and_(
                _role_consultorio_scope_condition(),
                select(Consultorio.id)
                .join(Complejo, Complejo.id == Consultorio.complejo_id)
                .where(Consultorio.id == UsuarioRol.consultorio_id, Complejo.institucion_id == institucion_id_col)
                .correlate_except(Consultorio, Complejo)
                .exists(),
            ),
            and_(
                _role_piso_scope_condition(),
                select(Piso.id)
                .join(Complejo, Complejo.id == Piso.complejo_id)
                .where(Piso.id == UsuarioRol.piso_id, Complejo.institucion_id == institucion_id_col)
                .correlate_except(Piso, Complejo)
                .exists(),
            ),
            and_(
                _role_torre_scope_condition(),
                select(Torre.id)
                .join(Complejo, Complejo.id == Torre.complejo_id)
                .where(Torre.id == UsuarioRol.torre_id, Complejo.institucion_id == institucion_id_col)
                .correlate_except(Torre, Complejo)
                .exists(),
            ),
            and_(
                _role_complejo_scope_condition(),
                select(Complejo.id)
                .where(Complejo.id == UsuarioRol.complejo_id, Complejo.institucion_id == institucion_id_col)
                .correlate_except(Complejo)
                .exists(),
            ),
            and_(_role_institucion_scope_condition(), UsuarioRol.institucion_id == institucion_id_col),
        ),
        today,
    )
    operator_location = _operator_scope_exists(
        user,
        or_(
            and_(
                AsignacionOperador.complejo_id.is_not(None),
                select(Complejo.id)
                .where(Complejo.id == AsignacionOperador.complejo_id, Complejo.institucion_id == institucion_id_col)
                .correlate_except(Complejo)
                .exists(),
            ),
            and_(
                AsignacionOperador.consultorio_id.is_not(None),
                select(Consultorio.id)
                .join(Complejo, Complejo.id == Consultorio.complejo_id)
                .where(Consultorio.id == AsignacionOperador.consultorio_id, Complejo.institucion_id == institucion_id_col)
                .correlate_except(Consultorio, Complejo)
                .exists(),
            ),
        ),
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


def _doctor_medico_access_predicate(user: Usuario, medico_id_col: Any, today: date | None = None) -> Any:
    own_medico = (
        select(Medico.id)
        .where(Medico.id == medico_id_col, Medico.usuario_id == user.id, Medico.activo.is_(True))
        .exists()
    )
    doctor_role_medico = _role_scope_exists(
        user,
        and_(UsuarioRol.medico_id == medico_id_col, Role.codigo == "MEDICO"),
        today,
    )
    return or_(own_medico, doctor_role_medico)


def _patient_belongs_to_medico_predicate(paciente_id_col: Any, medico_id_col: Any) -> Any:
    return (
        select(MedicoPaciente.paciente_id)
        .where(
            MedicoPaciente.paciente_id == paciente_id_col,
            MedicoPaciente.medico_id == medico_id_col,
            MedicoPaciente.activo.is_(True),
        )
        .exists()
    )


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


def _medico_consultorio_assignment_access_predicate(user: Usuario, consultorio_id_col: Any, today: date | None = None) -> Any:
    return (
        select(AsignacionMedicoConsultorio.id)
        .where(
            AsignacionMedicoConsultorio.consultorio_id == consultorio_id_col,
            *_active_medico_consultorio_conditions(today),
            _medico_access_predicate(user, AsignacionMedicoConsultorio.medico_id, today),
        )
        .exists()
    )


def _medico_piso_assignment_access_predicate(user: Usuario, piso_id_col: Any, today: date | None = None) -> Any:
    return (
        select(AsignacionMedicoConsultorio.id)
        .join(Consultorio, Consultorio.id == AsignacionMedicoConsultorio.consultorio_id)
        .where(
            Consultorio.piso_id == piso_id_col,
            *_active_medico_consultorio_conditions(today),
            _medico_access_predicate(user, AsignacionMedicoConsultorio.medico_id, today),
        )
        .exists()
    )


def _medico_torre_assignment_access_predicate(user: Usuario, torre_id_col: Any, today: date | None = None) -> Any:
    return (
        select(AsignacionMedicoConsultorio.id)
        .join(Consultorio, Consultorio.id == AsignacionMedicoConsultorio.consultorio_id)
        .join(Piso, Piso.id == Consultorio.piso_id)
        .where(
            Piso.torre_id == torre_id_col,
            *_active_medico_consultorio_conditions(today),
            _medico_access_predicate(user, AsignacionMedicoConsultorio.medico_id, today),
        )
        .exists()
    )


def _medico_complejo_assignment_access_predicate(user: Usuario, complejo_id_col: Any, today: date | None = None) -> Any:
    return (
        select(AsignacionMedicoConsultorio.id)
        .join(Consultorio, Consultorio.id == AsignacionMedicoConsultorio.consultorio_id)
        .where(
            Consultorio.complejo_id == complejo_id_col,
            *_active_medico_consultorio_conditions(today),
            _medico_access_predicate(user, AsignacionMedicoConsultorio.medico_id, today),
        )
        .exists()
    )


def _medico_institucion_assignment_access_predicate(user: Usuario, institucion_id_col: Any, today: date | None = None) -> Any:
    return (
        select(AsignacionMedicoConsultorio.id)
        .join(Consultorio, Consultorio.id == AsignacionMedicoConsultorio.consultorio_id)
        .join(Complejo, Complejo.id == Consultorio.complejo_id)
        .where(
            Complejo.institucion_id == institucion_id_col,
            *_active_medico_consultorio_conditions(today),
            _medico_access_predicate(user, AsignacionMedicoConsultorio.medico_id, today),
        )
        .exists()
    )


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


def institucion_catalog_access_predicate(db: Session, user: Usuario, today: date | None = None) -> Any:
    if user_has_global_access(db, user, today):
        return true()
    return or_(
        _unrestricted_location_access_predicate(user, today),
        _institucion_location_access_predicate(user, Institucion.id, today),
        _medico_institucion_assignment_access_predicate(user, Institucion.id, today),
    )


def complejo_catalog_access_predicate(db: Session, user: Usuario, today: date | None = None) -> Any:
    if user_has_global_access(db, user, today):
        return true()
    return or_(
        _unrestricted_location_access_predicate(user, today),
        _complejo_location_access_predicate(user, Complejo.id, Complejo.institucion_id, today),
        _medico_complejo_assignment_access_predicate(user, Complejo.id, today),
    )


def torre_catalog_access_predicate(db: Session, user: Usuario, today: date | None = None) -> Any:
    if user_has_global_access(db, user, today):
        return true()
    return or_(
        _unrestricted_location_access_predicate(user, today),
        _torre_location_access_predicate(user, Torre.id, Torre.complejo_id, today),
        _medico_torre_assignment_access_predicate(user, Torre.id, today),
    )


def consultorio_catalog_access_predicate(db: Session, user: Usuario, today: date | None = None) -> Any:
    if user_has_global_access(db, user, today):
        return true()
    consultorio_by_location = or_(
        _unrestricted_location_access_predicate(user, today),
        _location_access_predicate(
            user,
            Consultorio.id,
            Consultorio.piso_id,
            Consultorio.complejo_id,
            today,
        ),
    )
    consultorio_by_medico = _medico_consultorio_assignment_access_predicate(user, Consultorio.id, today)
    return or_(consultorio_by_location, consultorio_by_medico)


def piso_catalog_access_predicate(db: Session, user: Usuario, today: date | None = None) -> Any:
    if user_has_global_access(db, user, today):
        return true()
    return or_(
        _unrestricted_location_access_predicate(user, today),
        _piso_location_access_predicate(user, Piso.id, Piso.torre_id, Piso.complejo_id, today),
        _medico_piso_assignment_access_predicate(user, Piso.id, today),
    )


def pantalla_turnos_access_predicate(db: Session, user: Usuario, today: date | None = None) -> Any:
    if user_has_global_access(db, user, today):
        return true()
    return or_(
        _unrestricted_location_access_predicate(user, today),
        _piso_location_access_predicate(user, PantallaTurnos.piso_id, Piso.torre_id, PantallaTurnos.complejo_id, today),
    )


def _cita_access_predicate_for(
    db: Session,
    user: Usuario,
    consultorio_id_col: Any,
    piso_id_col: Any,
    complejo_id_col: Any,
    medico_id_col: Any,
    today: date | None = None,
) -> Any:
    if user_has_global_access(db, user, today):
        return true()
    return or_(
        _location_access_predicate(user, consultorio_id_col, piso_id_col, complejo_id_col, today),
        _medico_access_predicate(user, medico_id_col, today),
    )


def cita_access_predicate(db: Session, user: Usuario, today: date | None = None) -> Any:
    return _cita_access_predicate_for(
        db,
        user,
        Cita.consultorio_id,
        Cita.piso_id,
        Cita.complejo_id,
        Cita.medico_id,
        today,
    )


def cita_agenda_access_predicate(db: Session, user: Usuario, today: date | None = None) -> Any:
    if user_has_global_access(db, user, today):
        return true()
    patient_for_cita_medico = _patient_belongs_to_medico_predicate(Cita.paciente_id, Cita.medico_id)
    doctor_citas = and_(
        patient_for_cita_medico,
        _doctor_medico_access_predicate(user, Cita.medico_id, today),
    )
    staff_citas = and_(
        patient_for_cita_medico,
        _medico_access_predicate(user, Cita.medico_id, today),
    )
    admin_scoped_citas = and_(
        _role_scope_exists(user, Role.codigo == "ADMIN_NEGOCIO", today),
        cita_access_predicate(db, user, today),
    )
    return or_(doctor_citas, staff_citas, admin_scoped_citas)


def paciente_access_predicate(db: Session, user: Usuario, today: date | None = None) -> Any:
    if user_has_global_access(db, user, today):
        return true()
    medico_paciente = aliased(MedicoPaciente)
    cita = aliased(Cita)
    paciente_by_medico = (
        select(medico_paciente.paciente_id)
        .where(
            medico_paciente.paciente_id == Paciente.id,
            medico_paciente.activo.is_(True),
            _medico_access_predicate(user, medico_paciente.medico_id, today),
        )
        .correlate(Paciente)
        .exists()
    )
    paciente_by_cita = (
        select(cita.id)
        .where(
            cita.paciente_id == Paciente.id,
            _cita_access_predicate_for(
                db,
                user,
                cita.consultorio_id,
                cita.piso_id,
                cita.complejo_id,
                cita.medico_id,
                today,
            ),
        )
        .correlate(Paciente)
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
