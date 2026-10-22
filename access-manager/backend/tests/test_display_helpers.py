from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.display import next_appointment_consultorio_details, public_next_appointments
from app.models.complejo import Complejo
from app.models.display import TurnoDisplay
from app.models.flow import Cita
from app.models.operational import AsignacionMedicoConsultorio, Consultorio, ConsultorioCluster, Medico, Piso, Role, Torre, UsuarioRol
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioRead, UsuarioUpdate


def test_next_appointment_consultorio_location_details() -> None:
    screen_floor_id = uuid4()
    other_floor_id = uuid4()
    other_tower_floor_id = uuid4()
    screen_tower_id = uuid4()
    other_tower_id = uuid4()
    records = {
        (Piso, screen_floor_id): SimpleNamespace(
            id=screen_floor_id, torre_id=screen_tower_id, numero=1, nombre_visible="Piso 1"
        ),
        (Piso, other_floor_id): SimpleNamespace(
            id=other_floor_id, torre_id=screen_tower_id, numero=2, nombre_visible="Nivel 2"
        ),
        (Piso, other_tower_floor_id): SimpleNamespace(
            id=other_tower_floor_id, torre_id=other_tower_id, numero=3, nombre_visible="Piso 3"
        ),
        (Torre, other_tower_id): SimpleNamespace(nombre="Torre B"),
    }

    class FakeSession:
        def get(self, model, item_id):
            return records.get((model, item_id))

    db = FakeSession()
    screen = SimpleNamespace(piso_id=screen_floor_id)
    same_tower = SimpleNamespace(piso_id=other_floor_id, codigo="202", nombre_visible="Consultorio 202")
    other_tower = SimpleNamespace(piso_id=other_tower_floor_id, codigo="B03", nombre_visible=None)

    assert next_appointment_consultorio_details(db, screen, same_tower) == ("Piso Nivel 2", "202")
    assert next_appointment_consultorio_details(db, screen, other_tower) == ("Torre B - Piso 3", None)


@pytest.mark.parametrize("prefijo, expected", [("  Dra2  ", "Dra2 Ana Pérez"), ("  ", "Ana Pérez"), (None, "Ana Pérez")])
def test_next_appointments_use_saved_user_prefix(prefijo, expected) -> None:
    engine = create_engine("sqlite://")
    for model in (Usuario, Medico, Consultorio, ConsultorioCluster, Cita, TurnoDisplay,
                  AsignacionMedicoConsultorio, UsuarioRol, Role, Complejo, Piso):
        model.__table__.create(engine)
    timestamp = datetime(2026, 10, 22, 12, tzinfo=UTC)
    campus_id, floor_id, cluster_id = uuid4(), uuid4(), uuid4()

    with Session(engine) as db:
        payload = UsuarioCreate(prefijo=prefijo, nombre="Ana", apellidos="Pérez",
                                email="ana@example.com", password="ValidPassword1!")
        user = Usuario(**payload.model_dump(exclude={"password"}), password_hash="irrelevant")
        db.add(user)
        db.flush()
        db.refresh(user)
        assert UsuarioRead.model_validate(user).prefijo == (prefijo.strip() or None if prefijo else None)
        doctor = Medico(usuario_id=user.id, nombre="Ana", apellidos="Pérez", nombre_visible="  Ana Pérez  ")
        unlinked_doctor = Medico(nombre="Luis", apellidos="López")
        office = Consultorio(complejo_id=campus_id, piso_id=floor_id, codigo="101")
        db.add_all([doctor, unlinked_doctor, office])
        db.flush()
        db.add(ConsultorioCluster(consultorio_id=office.id, cluster_id=cluster_id))
        for index, medico in enumerate((doctor, unlinked_doctor)):
            db.add(AsignacionMedicoConsultorio(medico_id=medico.id, consultorio_id=office.id,
                                              fecha_inicio=timestamp.date()))
            db.add(Cita(paciente_id=uuid4(), medico_id=medico.id, consultorio_id=office.id,
                        complejo_id=campus_id, piso_id=floor_id, fecha_cita=timestamp.date(),
                        hora_cita=timestamp.time().replace(tzinfo=None), folio_turno=f"A{index:03}",
                        tipo="PROGRAMADA", estado="LLEGO_LOBBY"))
        db.commit()
        screen = SimpleNamespace(complejo_id=campus_id, consultorio_id=None, piso_id=None)

        rows = public_next_appointments(db, screen, [cluster_id], timestamp)
        assert {row.medico for row in rows} == {expected, "Luis López"}

        for value, expected_name in [("  Dr3  ", "Dr3 Ana Pérez"), ("  ", "Ana Pérez")]:
            update = UsuarioUpdate(prefijo=value)
            user.prefijo = update.prefijo
            db.commit()
            rows = public_next_appointments(db, screen, [cluster_id], timestamp)
            assert {row.medico for row in rows} == {expected_name, "Luis López"}

    engine.dispose()
