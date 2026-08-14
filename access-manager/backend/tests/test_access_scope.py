from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.models.complejo import Complejo
from app.models.display import PantallaTurnos
from app.models.flow import MedicoPaciente, Paciente
from app.models.institucion import Institucion
from app.models.operational import Consultorio, Piso, Torre
from app.models.usuario import Usuario
from app.services.access_scope import (
    complejo_catalog_access_predicate,
    consultorio_catalog_access_predicate,
    institucion_catalog_access_predicate,
    paciente_access_predicate,
    pantalla_turnos_access_predicate,
    piso_catalog_access_predicate,
    torre_catalog_access_predicate,
)


def test_patient_scope_compiles_with_medico_filter_join() -> None:
    db = SimpleNamespace(execute=lambda *_args, **_kwargs: SimpleNamespace(first=lambda: None))
    user = Usuario(
        id=uuid4(),
        apellidos="Demo",
        nombre="Médico",
        email="medico@example.com",
        password_hash="irrelevant",
    )

    query = (
        select(Paciente)
        .where(paciente_access_predicate(db, user))
        .join(MedicoPaciente, MedicoPaciente.paciente_id == Paciente.id)
        .where(MedicoPaciente.medico_id == uuid4(), MedicoPaciente.activo.is_(True))
    )

    compiled = str(query.compile(dialect=postgresql.dialect()))

    assert "medico_pacientes AS medico_pacientes_1" in compiled
    assert "FROM pisos, citas" not in compiled
    assert "FROM complejos, citas" not in compiled


def test_location_catalog_scope_predicates_compile() -> None:
    db = SimpleNamespace(execute=lambda *_args, **_kwargs: SimpleNamespace(first=lambda: None))
    user = Usuario(
        id=uuid4(),
        apellidos="Scope",
        nombre="Recepción",
        email="recepcion@example.com",
        password_hash="irrelevant",
    )
    today = date(2026, 8, 14)

    queries = [
        select(Institucion).where(institucion_catalog_access_predicate(db, user, today)),
        select(Complejo).where(complejo_catalog_access_predicate(db, user, today)),
        select(Torre).where(torre_catalog_access_predicate(db, user, today)),
        select(Piso).where(piso_catalog_access_predicate(db, user, today)),
        select(Consultorio).where(consultorio_catalog_access_predicate(db, user, today)),
        select(PantallaTurnos)
        .outerjoin(Piso, Piso.id == PantallaTurnos.piso_id)
        .where(pantalla_turnos_access_predicate(db, user, today)),
    ]

    compiled = "\n".join(str(query.compile(dialect=postgresql.dialect())) for query in queries)

    assert "usuario_roles" in compiled
    assert "asignaciones_operador" in compiled
    assert "medico_pacientes AS medico_pacientes_1" not in compiled
