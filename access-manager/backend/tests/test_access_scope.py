from __future__ import annotations

from datetime import date, time
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from app.models.complejo import Complejo
from app.models.display import PantallaTurnos
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
from app.api.contactos import search_institution_scope_for_user, search_institutions_for_user
from app.services.access_scope import (
    cita_agenda_access_predicate,
    complejo_catalog_access_predicate,
    consultorio_catalog_access_predicate,
    institucion_catalog_access_predicate,
    paciente_access_predicate,
    pantalla_turnos_access_predicate,
    piso_catalog_access_predicate,
    torre_catalog_access_predicate,
)


def create_scope_test_tables(engine) -> None:
    Usuario.metadata.create_all(
        engine,
        tables=[
            Usuario.__table__,
            Role.__table__,
            Institucion.__table__,
            Complejo.__table__,
            Torre.__table__,
            Piso.__table__,
            Consultorio.__table__,
            Medico.__table__,
            Operador.__table__,
            UsuarioRol.__table__,
            AsignacionMedicoConsultorio.__table__,
            AsignacionOperador.__table__,
            Paciente.__table__,
            MedicoPaciente.__table__,
            Cita.__table__,
        ],
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


def test_cita_agenda_scope_compiles_with_patient_medico_and_location() -> None:
    db = SimpleNamespace(execute=lambda *_args, **_kwargs: SimpleNamespace(first=lambda: None))
    user = Usuario(
        id=uuid4(),
        apellidos="Agenda",
        nombre="Recepción",
        email="agenda@example.com",
        password_hash="irrelevant",
    )

    query = select(Cita).where(cita_agenda_access_predicate(db, user, date(2026, 8, 17)))
    compiled = str(query.compile(dialect=postgresql.dialect()))

    assert "medico_pacientes" in compiled
    assert "usuario_roles" in compiled
    assert "asignaciones_operador" in compiled


def test_assistant_with_medico_scope_can_see_doctor_appointments_without_location_scope() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    create_scope_test_tables(engine)
    today = date(2026, 8, 20)

    with Session(engine) as db:
        assistant = Usuario(
            apellidos="Asistente",
            nombre="Medica",
            email="asistente@example.com",
            password_hash="irrelevant",
        )
        role = Role(codigo="ASISTENTE_MEDICO", nombre="Asistente medico", permisos={})
        medico = Medico(nombre="Medico", apellidos="Agenda")
        institucion = Institucion(nombre="Institucion")
        db.add_all([assistant, role, medico, institucion])
        db.flush()

        complejo = Complejo(institucion_id=institucion.id, nombre="Campus", zona_horaria="America/Mexico_City")
        db.add(complejo)
        db.flush()
        torre = Torre(complejo_id=complejo.id, nombre="Torre", numero_pisos=1)
        db.add(torre)
        db.flush()
        piso = Piso(complejo_id=complejo.id, torre_id=torre.id, numero=1, codigo="1", nombre_visible="Piso 1")
        db.add(piso)
        db.flush()
        consultorio = Consultorio(complejo_id=complejo.id, piso_id=piso.id, codigo="101")
        paciente = Paciente(folio_paciente="P0001", nombre="Paciente", apellido_paterno="Demo", celular="5550000000")
        db.add_all([consultorio, paciente])
        db.flush()

        db.add_all(
            [
                UsuarioRol(usuario_id=assistant.id, rol_id=role.id, medico_id=medico.id, fecha_inicio=today),
                MedicoPaciente(medico_id=medico.id, paciente_id=paciente.id),
                Cita(
                    tipo="PROGRAMADA",
                    paciente_id=paciente.id,
                    medico_id=medico.id,
                    consultorio_id=consultorio.id,
                    complejo_id=complejo.id,
                    piso_id=piso.id,
                    fecha_cita=today,
                    hora_cita=time(10, 0),
                    folio_turno="A001",
                ),
            ]
        )
        db.commit()

        citas = list(db.execute(select(Cita).where(cita_agenda_access_predicate(db, assistant, today))).scalars())

    assert len(citas) == 1


def test_contact_search_institutions_for_assistant_use_assigned_medico_scope() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    create_scope_test_tables(engine)
    today = date(2026, 8, 21)

    with Session(engine) as db:
        assistant = Usuario(
            apellidos="Asistente",
            nombre="Medica",
            email="asistente-contactos@example.com",
            password_hash="irrelevant",
        )
        assistant_role = Role(codigo="ASISTENTE_MEDICO", nombre="Asistente medico", permisos={})
        medico_role = Role(codigo="MEDICO", nombre="Medico", permisos={})
        medico = Medico(nombre="Medico", apellidos="Contactos")
        institucion = Institucion(nombre="Institucion Contactos")
        otra_institucion = Institucion(nombre="Otra Institucion")
        db.add_all([assistant, assistant_role, medico_role, medico, institucion, otra_institucion])
        db.flush()

        complejo = Complejo(institucion_id=institucion.id, nombre="Campus Contactos", zona_horaria="America/Mexico_City")
        otro_complejo = Complejo(
            institucion_id=otra_institucion.id,
            nombre="Campus Sin Medico",
            zona_horaria="America/Mexico_City",
        )
        db.add_all([complejo, otro_complejo])
        db.flush()
        torre = Torre(complejo_id=complejo.id, nombre="Torre", numero_pisos=1)
        db.add(torre)
        db.flush()
        piso = Piso(complejo_id=complejo.id, torre_id=torre.id, numero=1, codigo="1", nombre_visible="Piso 1")
        db.add(piso)
        db.flush()
        consultorio = Consultorio(complejo_id=complejo.id, piso_id=piso.id, codigo="101")
        db.add(consultorio)
        db.flush()

        db.add_all(
            [
                UsuarioRol(usuario_id=assistant.id, rol_id=assistant_role.id, medico_id=medico.id, fecha_inicio=today),
                UsuarioRol(usuario_id=assistant.id, rol_id=assistant_role.id, medico_id=medico.id, fecha_inicio=today),
                UsuarioRol(usuario_id=uuid4(), rol_id=medico_role.id, medico_id=medico.id, complejo_id=complejo.id, fecha_inicio=today),
                AsignacionMedicoConsultorio(
                    medico_id=medico.id,
                    consultorio_id=consultorio.id,
                    fecha_inicio=today,
                ),
            ]
        )
        db.commit()

        instituciones = search_institutions_for_user(db, assistant, today)

    assert [item.id for item in instituciones] == [institucion.id]


def test_contact_search_institutions_for_medico_use_assigned_scope_without_duplicates() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    create_scope_test_tables(engine)
    today = date(2026, 8, 21)

    with Session(engine) as db:
        medico_user = Usuario(
            apellidos="Contactos",
            nombre="Medico",
            email="medico-contactos@example.com",
            password_hash="irrelevant",
        )
        medico_role = Role(codigo="MEDICO", nombre="Medico", permisos={})
        medico = Medico(nombre="Medico", apellidos="Contactos", usuario_id=medico_user.id)
        institucion = Institucion(nombre="Institucion Medico")
        otra_institucion = Institucion(nombre="Otra Institucion")
        db.add_all([medico_user, medico_role, medico, institucion, otra_institucion])
        db.flush()

        db.add_all(
            [
                UsuarioRol(usuario_id=medico_user.id, rol_id=medico_role.id, institucion_id=institucion.id, fecha_inicio=today),
                UsuarioRol(usuario_id=medico_user.id, rol_id=medico_role.id, institucion_id=institucion.id, fecha_inicio=today),
            ]
        )
        db.commit()

        instituciones = search_institutions_for_user(db, medico_user, today)

    assert [item.id for item in instituciones] == [institucion.id]


def test_contact_search_institutions_without_assigned_scope_allow_all() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    create_scope_test_tables(engine)
    today = date(2026, 8, 21)

    with Session(engine) as db:
        admin = Usuario(
            apellidos="Negocio",
            nombre="Admin",
            email="admin-contactos@example.com",
            password_hash="irrelevant",
        )
        admin_role = Role(codigo="ADMIN_NEGOCIO", nombre="Admin negocio", permisos={})
        institucion_a = Institucion(nombre="Alpha")
        institucion_b = Institucion(nombre="Beta")
        db.add_all([admin, admin_role, institucion_a, institucion_b])
        db.flush()
        db.add(UsuarioRol(usuario_id=admin.id, rol_id=admin_role.id, fecha_inicio=today))
        db.commit()

        institution_ids, allow_all = search_institution_scope_for_user(db, admin, today)
        instituciones = search_institutions_for_user(db, admin, today)

    assert institution_ids == set()
    assert allow_all is True
    assert [item.nombre for item in instituciones] == ["Alpha", "Beta"]


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
    assert "asignaciones_medico_consultorio" in compiled
    assert "roles.codigo != " in compiled
    assert "roles.codigo = " in compiled
    assert "usuario_roles.consultorio_id IS NOT NULL AND usuario_roles.consultorio_id = consultorios.id" in compiled
    assert "usuario_roles.consultorio_id IS NULL AND usuario_roles.piso_id IS NOT NULL" in compiled
    assert "medico_pacientes AS medico_pacientes_1" not in compiled
