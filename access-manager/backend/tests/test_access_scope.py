from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.models.flow import MedicoPaciente, Paciente
from app.models.usuario import Usuario
from app.services.access_scope import paciente_access_predicate


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
