from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.display import PantallaTurnos, PantallaTurnosCluster
from app.models.operational import UsuarioRol
from app.services.seed_admins import main as seed_admins
from app.services.folio_service import FOLIO_TURNO_ALPHABET, is_valid_turn_folio


@pytest.fixture(scope="session", autouse=True)
def seed_data() -> None:
    seed_admins()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def auth_headers(client: TestClient) -> dict[str, str]:
    password = os.getenv("SEED_ADMIN_PASSWORD", "change-me-temporary-admin-password")
    response = client.post("/api/auth/login", json={"email": "admin1@example.com", "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def assert_created(response):
    assert response.status_code == 201, response.text
    return response.json()


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_patient_can_use_preferred_name_only(client: TestClient, auth_headers: dict[str, str]) -> None:
    suffix = uuid4().hex[:8]

    paciente = assert_created(
        client.post(
            "/api/pacientes",
            headers=auth_headers,
            json={
                "nombre_preferido": f"Alias {suffix}",
                "fecha_nacimiento": "1990-01-31",
            },
        )
    )

    assert paciente["nombre"] is None
    assert paciente["apellido_paterno"] is None
    assert paciente["nombre_preferido"] == f"Alias {suffix}"


def test_forced_password_change_flow(client: TestClient, auth_headers: dict[str, str]) -> None:
    suffix = uuid4().hex[:8]
    initial_password = "Temporal123!"
    new_password = "NuevaTemporal123!"

    user = assert_created(
        client.post(
            "/api/usuarios",
            headers=auth_headers,
            json={
                "apellidos": "Negocio",
                "nombre": f"Admin Negocio {suffix}",
                "email": f"admin-negocio-{suffix}@example.com",
                "password": initial_password,
                "force_password_change": True,
            },
        )
    )
    assert user["force_password_change"] is True

    roles_response = client.get("/api/roles", headers=auth_headers)
    assert roles_response.status_code == 200, roles_response.text
    admin_negocio_role = next(role for role in roles_response.json() if role["codigo"] == "ADMIN_NEGOCIO")
    assert_created(
        client.post(
            "/api/usuario-roles",
            headers=auth_headers,
            json={"usuario_id": user["id"], "rol_id": admin_negocio_role["id"]},
        )
    )

    login_response = client.post("/api/auth/login", json={"email": user["email"], "password": initial_password})
    assert login_response.status_code == 200, login_response.text
    forced_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    me_response = client.get("/api/auth/me", headers=forced_headers)
    assert me_response.status_code == 200, me_response.text
    assert me_response.json()["force_password_change"] is True
    assert "Administrador de negocio" in me_response.json()["roles"]

    profile_response = client.patch(
        "/api/auth/me",
        headers=forced_headers,
        json={"correo_alterno": f"ALTERNO-{suffix}@Example.COM"},
    )
    assert profile_response.status_code == 200, profile_response.text
    assert profile_response.json()["correo_alterno"] == f"alterno-{suffix}@example.com"
    assert "Administrador de negocio" in profile_response.json()["roles"]

    clear_profile_response = client.patch(
        "/api/auth/me",
        headers=forced_headers,
        json={"correo_alterno": ""},
    )
    assert clear_profile_response.status_code == 200, clear_profile_response.text
    assert clear_profile_response.json()["correo_alterno"] is None

    blocked_response = client.get("/api/roles", headers=forced_headers)
    assert blocked_response.status_code == 403, blocked_response.text
    assert blocked_response.json()["detail"] == "Debe cambiar su contraseña antes de continuar."

    wrong_password_response = client.post(
        "/api/auth/password",
        headers=forced_headers,
        json={"current_password": "incorrecta", "new_password": new_password},
    )
    assert wrong_password_response.status_code == 401, wrong_password_response.text

    change_response = client.post(
        "/api/auth/password",
        headers=forced_headers,
        json={"current_password": initial_password, "new_password": new_password},
    )
    assert change_response.status_code == 200, change_response.text
    assert change_response.json()["force_password_change"] is False

    old_login_response = client.post("/api/auth/login", json={"email": user["email"], "password": initial_password})
    assert old_login_response.status_code == 401, old_login_response.text

    new_login_response = client.post("/api/auth/login", json={"email": user["email"], "password": new_password})
    assert new_login_response.status_code == 200, new_login_response.text
    active_headers = {"Authorization": f"Bearer {new_login_response.json()['access_token']}"}
    roles_after_change = client.get("/api/roles", headers=active_headers)
    assert roles_after_change.status_code == 200, roles_after_change.text


def test_admin_can_reset_user_password(client: TestClient, auth_headers: dict[str, str]) -> None:
    suffix = uuid4().hex[:8]
    initial_password = "Temporal123!"
    reset_password = "ResetTemporal123!"

    user = assert_created(
        client.post(
            "/api/usuarios",
            headers=auth_headers,
            json={
                "apellidos": "Reset",
                "nombre": f"Usuario Reset {suffix}",
                "email": f"Usuario-Reset-{suffix}@Example.COM",
                "password": initial_password,
            },
        )
    )
    assert user["email"] == f"usuario-reset-{suffix}@example.com"

    initial_login = client.post(
        "/api/auth/login",
        json={"email": f"USUARIO-RESET-{suffix}@EXAMPLE.COM", "password": initial_password},
    )
    assert initial_login.status_code == 200, initial_login.text

    reset_response = client.patch(
        f"/api/usuarios/{user['id']}",
        headers=auth_headers,
        json={"password": reset_password},
    )
    assert reset_response.status_code == 200, reset_response.text

    old_login = client.post("/api/auth/login", json={"email": user["email"], "password": initial_password})
    assert old_login.status_code == 401, old_login.text

    reset_login = client.post("/api/auth/login", json={"email": user["email"], "password": reset_password})
    assert reset_login.status_code == 200, reset_login.text


def test_user_password_requires_number(client: TestClient, auth_headers: dict[str, str]) -> None:
    suffix = uuid4().hex[:8]
    valid_password = "Temporal123!"
    invalid_password = "temporal"

    invalid_create = client.post(
        "/api/usuarios",
        headers=auth_headers,
        json={
            "apellidos": "Password",
            "nombre": f"Usuario Password {suffix}",
            "email": f"password-{suffix}@example.com",
            "password": invalid_password,
        },
    )
    assert invalid_create.status_code == 422, invalid_create.text
    assert "al menos 1 número" in invalid_create.text

    user = assert_created(
        client.post(
            "/api/usuarios",
            headers=auth_headers,
            json={
                "apellidos": "Password",
                "nombre": f"Usuario Password {suffix}",
                "email": f"password-{suffix}@example.com",
                "password": valid_password,
            },
        )
    )

    invalid_reset = client.patch(
        f"/api/usuarios/{user['id']}",
        headers=auth_headers,
        json={"password": invalid_password},
    )
    assert invalid_reset.status_code == 422, invalid_reset.text
    assert "al menos 1 número" in invalid_reset.text

    login_response = client.post("/api/auth/login", json={"email": user["email"], "password": valid_password})
    assert login_response.status_code == 200, login_response.text
    user_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    invalid_self_change = client.post(
        "/api/auth/password",
        headers=user_headers,
        json={"current_password": valid_password, "new_password": invalid_password},
    )
    assert invalid_self_change.status_code == 422, invalid_self_change.text
    assert "al menos 1 número" in invalid_self_change.text


def test_usuario_rol_rejects_self_medico_assignment(client: TestClient, auth_headers: dict[str, str]) -> None:
    suffix = uuid4().hex[:8]

    user = assert_created(
        client.post(
            "/api/usuarios",
            headers=auth_headers,
            json={
                "apellidos": f"Self {suffix}",
                "nombre": f"Usuario Médico {suffix}",
                "email": f"usuario-medico-{suffix}@example.com",
                "password": "Temporal123!",
            },
        )
    )
    other_user = assert_created(
        client.post(
            "/api/usuarios",
            headers=auth_headers,
            json={
                "apellidos": f"Otro {suffix}",
                "nombre": f"Médico Asignable {suffix}",
                "email": f"medico-asignable-{suffix}@example.com",
                "password": "Temporal123!",
            },
        )
    )

    roles_response = client.get("/api/roles", headers=auth_headers)
    assert roles_response.status_code == 200, roles_response.text
    medico_role = next(role for role in roles_response.json() if role["codigo"] == "MEDICO")

    self_medico = assert_created(
        client.post(
            "/api/medicos",
            headers=auth_headers,
            json={
                "usuario_id": user["id"],
                "nombre": "Médico",
                "apellidos": f"Propio {suffix}",
            },
        )
    )
    unlinked_self_medico = assert_created(
        client.post(
            "/api/medicos",
            headers=auth_headers,
            json={
                "nombre": user["nombre"],
                "apellidos": user["apellidos"],
            },
        )
    )
    other_medico = assert_created(
        client.post(
            "/api/medicos",
            headers=auth_headers,
            json={
                "usuario_id": other_user["id"],
                "nombre": "Médico",
                "apellidos": f"Asignable {suffix}",
            },
        )
    )

    create_response = client.post(
        "/api/usuario-roles",
        headers=auth_headers,
        json={
            "usuario_id": user["id"],
            "rol_id": medico_role["id"],
            "medico_id": self_medico["id"],
            "fecha_inicio": "2026-08-12",
        },
    )
    assert create_response.status_code == 422, create_response.text
    assert "no puede asignarse a sí mismo" in create_response.text

    unlinked_create_response = client.post(
        "/api/usuario-roles",
        headers=auth_headers,
        json={
            "usuario_id": user["id"],
            "rol_id": medico_role["id"],
            "medico_id": unlinked_self_medico["id"],
            "fecha_inicio": "2026-08-12",
        },
    )
    assert unlinked_create_response.status_code == 422, unlinked_create_response.text
    assert "no puede asignarse a sí mismo" in unlinked_create_response.text

    valid_assignment = assert_created(
        client.post(
            "/api/usuario-roles",
            headers=auth_headers,
            json={
                "usuario_id": user["id"],
                "rol_id": medico_role["id"],
                "medico_id": other_medico["id"],
                "fecha_inicio": "2026-08-12",
            },
        )
    )
    update_response = client.patch(
        f"/api/usuario-roles/{valid_assignment['id']}",
        headers=auth_headers,
        json={"medico_id": self_medico["id"]},
    )
    assert update_response.status_code == 422, update_response.text
    assert "no puede asignarse a sí mismo" in update_response.text

    with SessionLocal() as db:
        historical_assignment = UsuarioRol(
            usuario_id=UUID(user["id"]),
            rol_id=UUID(medico_role["id"]),
            medico_id=UUID(self_medico["id"]),
            fecha_inicio=date(2026, 8, 12),
            activo=True,
        )
        db.add(historical_assignment)
        db.commit()
        db.refresh(historical_assignment)
        historical_assignment_id = str(historical_assignment.id)

    deactivate_response = client.patch(
        f"/api/usuario-roles/{historical_assignment_id}",
        headers=auth_headers,
        json={"activo": False},
    )
    assert deactivate_response.status_code == 200, deactivate_response.text
    assert deactivate_response.json()["activo"] is False


def test_usuario_rol_rejects_overlapping_active_medico_assignment(client: TestClient, auth_headers: dict[str, str]) -> None:
    suffix = uuid4().hex[:8]

    user = assert_created(
        client.post(
            "/api/usuarios",
            headers=auth_headers,
            json={
                "apellidos": f"Agenda {suffix}",
                "nombre": f"Usuario Agenda {suffix}",
                "email": f"usuario-agenda-{suffix}@example.com",
                "password": "Temporal123!",
            },
        )
    )
    medico_user = assert_created(
        client.post(
            "/api/usuarios",
            headers=auth_headers,
            json={
                "apellidos": f"Doctor {suffix}",
                "nombre": f"Médico Agenda {suffix}",
                "email": f"medico-agenda-{suffix}@example.com",
                "password": "Temporal123!",
            },
        )
    )
    roles_response = client.get("/api/roles", headers=auth_headers)
    assert roles_response.status_code == 200, roles_response.text
    medico_role = next(role for role in roles_response.json() if role["codigo"] == "MEDICO")
    medico = assert_created(
        client.post(
            "/api/medicos",
            headers=auth_headers,
            json={
                "usuario_id": medico_user["id"],
                "nombre": "Médico",
                "apellidos": f"Agenda {suffix}",
            },
        )
    )

    assert_created(
        client.post(
            "/api/usuario-roles",
            headers=auth_headers,
            json={
                "usuario_id": user["id"],
                "rol_id": medico_role["id"],
                "medico_id": medico["id"],
                "fecha_inicio": "2026-09-01",
                "fecha_fin": "2026-09-10",
            },
        )
    )

    overlap_response = client.post(
        "/api/usuario-roles",
        headers=auth_headers,
        json={
            "usuario_id": user["id"],
            "rol_id": medico_role["id"],
            "medico_id": medico["id"],
            "fecha_inicio": "2026-09-10",
            "fecha_fin": "2026-09-20",
        },
    )
    assert overlap_response.status_code == 409, overlap_response.text
    assert "fechas traslapadas" in overlap_response.text

    non_overlap = assert_created(
        client.post(
            "/api/usuario-roles",
            headers=auth_headers,
            json={
                "usuario_id": user["id"],
                "rol_id": medico_role["id"],
                "medico_id": medico["id"],
                "fecha_inicio": "2026-09-11",
                "fecha_fin": "2026-09-20",
            },
        )
    )
    assert non_overlap["activo"] is True


def test_operational_catalog_flow(client: TestClient, auth_headers: dict[str, str]) -> None:
    suffix = uuid4().hex[:8]

    institucion = assert_created(
        client.post(
            "/api/instituciones",
            headers=auth_headers,
            json={"nombre": f"Institución Test {suffix}", "razon_social": f"Institución Test {suffix} S.A."},
        )
    )
    complejo = assert_created(
        client.post(
            "/api/complejos",
            headers=auth_headers,
            json={
                "institucion_id": institucion["id"],
                "nombre": f"Torre Test {suffix}",
                "zona_horaria": "America/Mexico_City",
            },
        )
    )
    torre = assert_created(
        client.post(
            "/api/torres",
            headers=auth_headers,
            json={
                "complejo_id": complejo["id"],
                "nombre": f"Torre Test {suffix}",
                "numero_pisos": 20,
            },
        )
    )
    pisos_response = client.get("/api/pisos", headers=auth_headers)
    assert pisos_response.status_code == 200, pisos_response.text
    piso = next(item for item in pisos_response.json() if item["torre_id"] == torre["id"] and item["numero"] == 1)
    update_response = client.patch(
        f"/api/pisos/{piso['id']}",
        headers=auth_headers,
        json={
            "codigo": f"T-{suffix}",
            "nombre_visible": f"Piso Test {suffix}",
            "descripcion": "Actualizado por prueba automatizada.",
        },
    )
    assert update_response.status_code == 200, update_response.text
    piso = update_response.json()

    deactivate_response = client.post(f"/api/pisos/{piso['id']}/desactivar", headers=auth_headers)
    assert deactivate_response.status_code == 200, deactivate_response.text
    assert deactivate_response.json()["activo"] is False

    activate_response = client.post(f"/api/pisos/{piso['id']}/activar", headers=auth_headers)
    assert activate_response.status_code == 200, activate_response.text
    assert activate_response.json()["activo"] is True

    sala = assert_created(
        client.post(
            "/api/salas-espera",
            headers=auth_headers,
            json={
                "complejo_id": complejo["id"],
                "piso_id": piso["id"],
                "nombre": f"Sala Test {suffix}",
                "capacidad_estimada": 12,
            },
        )
    )
    assert sala["activa"] is True

    cluster = assert_created(
        client.post(
            "/api/clusters-turnos",
            headers=auth_headers,
            json={
                "complejo_id": complejo["id"],
                "piso_id": piso["id"],
                "nombre": f"Cluster Test {suffix}",
            },
        )
    )
    pantalla = assert_created(
        client.post(
            "/api/pantallas-turnos",
            headers=auth_headers,
            json={
                "codigo_dispositivo": f"display-{suffix}",
                "nombre": f"Pantalla Test {suffix}",
                "complejo_id": complejo["id"],
                "piso_id": piso["id"],
                "cluster_ids": [cluster["id"]],
                "polling_interval_seconds": 2,
                "segundos_resaltado": 5,
                "segundos_visible": 30,
                "max_turnos_visibles": 5,
            },
        )
    )
    assert pantalla["polling_interval_seconds"] == 2

    consulta_pantallas = client.get(
        "/api/consultas-clusters-pantallas",
        headers=auth_headers,
        params={
            "institucion_id": institucion["id"],
            "complejo_id": complejo["id"],
            "torre_id": torre["id"],
            "piso_id": piso["id"],
            "estado": "activa",
        },
    )
    assert consulta_pantallas.status_code == 200, consulta_pantallas.text
    pantalla_asignada = next(item for item in consulta_pantallas.json() if item["id"] == pantalla["id"])
    assert pantalla_asignada["cluster_ids"] == [cluster["id"]]
    assert pantalla_asignada["clusters"][0]["id"] == cluster["id"]
    assert pantalla_asignada["institucion"] == institucion["nombre"]
    assert pantalla_asignada["campus"] == complejo["nombre"]
    assert pantalla_asignada["torre"] == torre["nombre"]
    assert pantalla_asignada["piso"] == piso["nombre_visible"]

    pantalla_sin_cluster = assert_created(
        client.post(
            "/api/pantallas-turnos",
            headers=auth_headers,
            json={
                "codigo_dispositivo": f"display-sin-cluster-{suffix}",
                "nombre": f"Pantalla Sin Cluster {suffix}",
                "complejo_id": complejo["id"],
                "piso_id": piso["id"],
                "cluster_ids": [cluster["id"]],
            },
        )
    )
    with SessionLocal() as db:
        db.query(PantallaTurnosCluster).filter(
            PantallaTurnosCluster.pantalla_id == UUID(pantalla_sin_cluster["id"])
        ).delete(synchronize_session=False)
        pantalla_row = db.get(PantallaTurnos, UUID(pantalla_sin_cluster["id"]))
        pantalla_row.cluster_espera_id = None
        db.commit()

    consulta_pantallas_sin_cluster = client.get(
        "/api/consultas-clusters-pantallas",
        headers=auth_headers,
        params={"complejo_id": complejo["id"], "sin_cluster": True},
    )
    assert consulta_pantallas_sin_cluster.status_code == 200, consulta_pantallas_sin_cluster.text
    assert any(item["id"] == pantalla_sin_cluster["id"] and item["clusters"] == [] for item in consulta_pantallas_sin_cluster.json())

    consultorio = assert_created(
        client.post(
            "/api/consultorios",
            headers=auth_headers,
            json={
                "complejo_id": complejo["id"],
                "piso_id": piso["id"],
                "codigo": f"C-{suffix}",
                "nombre_visible": f"Consultorio Test {suffix}",
                "notas": f"Nota consultorio {suffix}",
                "cluster_ids": [cluster["id"]],
            },
        )
    )
    assert consultorio["notas"] == f"Nota consultorio {suffix}"
    consultorio_sin_cluster_response = client.post(
        "/api/consultorios",
        headers=auth_headers,
        json={
            "complejo_id": complejo["id"],
            "piso_id": piso["id"],
            "codigo": f"SC-{suffix}",
            "nombre_visible": f"Sin Cluster {suffix}",
            "cluster_ids": [],
        },
    )
    assert consultorio_sin_cluster_response.status_code == 422, consultorio_sin_cluster_response.text

    consulta_con_cluster = client.get(
        "/api/consultas-clusters-consultorios/por-consultorio",
        headers=auth_headers,
        params={"torre_id": torre["id"], "q": "Consultorio Test"},
    )
    assert consulta_con_cluster.status_code == 200, consulta_con_cluster.text
    consultorio_asignado = next(item for item in consulta_con_cluster.json() if item["id"] == consultorio["id"])
    assert consultorio_asignado["cluster_ids"] == [cluster["id"]]
    assert consultorio_asignado["clusters"][0]["id"] == cluster["id"]

    consulta_por_piso = client.get(
        "/api/consultas-clusters-consultorios/por-piso",
        headers=auth_headers,
        params={"torre_id": torre["id"], "piso_id": piso["id"]},
    )
    assert consulta_por_piso.status_code == 200, consulta_por_piso.text
    piso_consulta = consulta_por_piso.json()[0]
    assert piso_consulta["piso"] == piso["nombre_visible"]
    assert piso_consulta["clusters"][0]["activo"] is True
    assert piso_consulta["clusters"][0]["consultorios"][0]["consultorio"] == consultorio["nombre_visible"]
    assert piso_consulta["consultorios_sin_cluster"] == []

    medico_user = assert_created(
        client.post(
            "/api/usuarios",
            headers=auth_headers,
            json={
                "apellidos": f"Test {suffix}",
                "nombre": f"Médico Test {suffix}",
                "email": f"medico-{suffix}@example.com",
                "password": "Temporal123!",
            },
        )
    )
    operador_user = assert_created(
        client.post(
            "/api/usuarios",
            headers=auth_headers,
            json={
                "apellidos": f"Test {suffix}",
                "nombre": f"Operador Test {suffix}",
                "email": f"operador-{suffix}@example.com",
                "password": "Temporal123!",
            },
        )
    )

    roles_response = client.get("/api/roles", headers=auth_headers)
    assert roles_response.status_code == 200, roles_response.text
    medico_role = next(role for role in roles_response.json() if role["codigo"] == "MEDICO")
    operador_role = next(role for role in roles_response.json() if role["codigo"] == "OPERADOR")

    assert_created(
        client.post(
            "/api/usuario-roles",
            headers=auth_headers,
            json={
                "usuario_id": medico_user["id"],
                "rol_id": medico_role["id"],
                "institucion_id": institucion["id"],
                "complejo_id": complejo["id"],
            },
        )
    )
    assert_created(
        client.post(
            "/api/usuario-roles",
            headers=auth_headers,
            json={
                "usuario_id": operador_user["id"],
                "rol_id": operador_role["id"],
                "institucion_id": institucion["id"],
                "complejo_id": complejo["id"],
            },
        )
    )

    admin_relogin = client.post(
        "/api/auth/login",
        json={
            "email": "admin1@example.com",
            "password": os.getenv("SEED_ADMIN_PASSWORD", "change-me-temporary-admin-password"),
        },
    )
    assert admin_relogin.status_code == 200, admin_relogin.text

    for email in (medico_user["email"], operador_user["email"]):
        login_response = client.post("/api/auth/login", json={"email": email, "password": "Temporal123!"})
        assert login_response.status_code == 200, login_response.text
        assert login_response.json()["access_token"]

    medico = assert_created(
        client.post(
            "/api/medicos",
            headers=auth_headers,
            json={
                "usuario_id": medico_user["id"],
                "nombre": "Médico",
                "apellidos": f"Test {suffix}",
                "nombre_visible": f"Dr. Test {suffix}",
            },
        )
    )
    operador = assert_created(
        client.post(
            "/api/operadores",
            headers=auth_headers,
            json={"usuario_id": operador_user["id"]},
        )
    )

    asignacion_medico = assert_created(
        client.post(
            "/api/asignaciones-medico-consultorio",
            headers=auth_headers,
            json={
                "medico_id": medico["id"],
                "consultorio_id": consultorio["id"],
                "fecha_inicio": "2026-06-01",
                "dias_semana": "L,M,X,J,V",
            },
        )
    )
    assert asignacion_medico["activo"] is True

    asignacion_operador = assert_created(
        client.post(
            "/api/asignaciones-operador",
            headers=auth_headers,
            json={
                "operador_id": operador["id"],
                "consultorio_id": consultorio["id"],
                "complejo_id": complejo["id"],
                "fecha_inicio": "2026-06-01",
                "prioridad": 50,
            },
        )
    )
    assert asignacion_operador["activo"] is True

    paciente = assert_created(
        client.post(
            "/api/pacientes",
            headers=auth_headers,
            json={
                "nombre": "Paciente",
                "apellido_paterno": f"Test {suffix}",
                "celular": f"555{suffix[:7]}",
            },
        )
    )
    cita = assert_created(
        client.post(
            "/api/citas",
            headers=auth_headers,
            json={
                "tipo": "PROGRAMADA",
                "paciente_id": paciente["id"],
                "medico_id": medico["id"],
                "consultorio_id": consultorio["id"],
                "complejo_id": complejo["id"],
                "piso_id": piso["id"],
                "fecha_cita": "2026-06-09",
                "hora_cita": "10:00",
                "origen": "TEST",
            },
        )
    )
    cita_id = cita["id"]

    llamado = assert_created(client.post(f"/api/citas/{cita_id}/llamar", headers=auth_headers))
    assert len(llamado["turno"]) == 4
    assert llamado["consultorio"] == consultorio["nombre_visible"]
    assert llamado["texto"] == f"Paciente Paciente T* a consultorio Test {suffix}"
    assert llamado["llamado_numero"] == 1
    assert llamado["estado_cita"] == "AGENDADA"

    public_response = client.get(f"/api/public-display/display-{suffix}/turnos")
    assert public_response.status_code == 200, public_response.text
    public_payload = public_response.json()
    assert public_payload["config"]["polling_interval_seconds"] == 2
    assert public_payload["turnos"][0]["turno"] == llamado["turno"]
    assert public_payload["turnos"][0]["texto"] == llamado["texto"]
    assert set(public_payload["turnos"][0].keys()) == {"turno", "consultorio", "texto", "estado", "llamado_en", "resaltado"}

    recientes_response = client.get(
        "/api/turnos-display/recientes",
        headers=auth_headers,
        params={"complejo_id": complejo["id"], "piso_id": piso["id"], "minutos": 30},
    )
    assert recientes_response.status_code == 200, recientes_response.text
    reciente = recientes_response.json()[0]
    assert reciente["texto"] == llamado["texto"]
    assert reciente["llamado_numero"] == 1
    assert reciente["estado_cita"] == "AGENDADA"
    assert set(reciente.keys()) == {"cita_id", "turno", "consultorio", "texto", "llamado_en", "estado", "estado_cita", "llamado_numero"}

    audit_response = client.get("/api/auditoria", headers=auth_headers)
    assert audit_response.status_code == 200, audit_response.text
    events = {item["evento"] for item in audit_response.json()}
    assert "CONSULTORIO_CREADO" in events
    assert "ASIGNACION_OPERADOR_CREADA" in events
    assert "TURNO_LLAMADO" in events


def test_citas_accept_legacy_display_cluster_assignment(client: TestClient, auth_headers: dict[str, str]) -> None:
    suffix = uuid4().hex[:8]

    institucion = assert_created(
        client.post(
            "/api/instituciones",
            headers=auth_headers,
            json={"nombre": f"Institución Legacy {suffix}", "razon_social": f"Institución Legacy {suffix} S.A."},
        )
    )
    complejo = assert_created(
        client.post(
            "/api/complejos",
            headers=auth_headers,
            json={
                "institucion_id": institucion["id"],
                "nombre": f"Campus Legacy {suffix}",
                "zona_horaria": "America/Mexico_City",
            },
        )
    )
    torre = assert_created(
        client.post(
            "/api/torres",
            headers=auth_headers,
            json={"complejo_id": complejo["id"], "nombre": f"Torre Legacy {suffix}", "numero_pisos": 1},
        )
    )
    pisos_response = client.get("/api/pisos", headers=auth_headers)
    assert pisos_response.status_code == 200, pisos_response.text
    piso = next(item for item in pisos_response.json() if item["torre_id"] == torre["id"] and item["numero"] == 1)
    cluster = assert_created(
        client.post(
            "/api/clusters-turnos",
            headers=auth_headers,
            json={"complejo_id": complejo["id"], "piso_id": piso["id"], "nombre": f"Cluster Legacy {suffix}"},
        )
    )
    pantalla = assert_created(
        client.post(
            "/api/pantallas-turnos",
            headers=auth_headers,
            json={
                "codigo_dispositivo": f"display-legacy-{suffix}",
                "nombre": f"Pantalla Legacy {suffix}",
                "complejo_id": complejo["id"],
                "piso_id": piso["id"],
                "cluster_ids": [cluster["id"]],
            },
        )
    )
    assert pantalla["cluster_espera_id"] == cluster["id"]

    with SessionLocal() as db:
        db.query(PantallaTurnosCluster).filter(PantallaTurnosCluster.pantalla_id == UUID(pantalla["id"])).delete(
            synchronize_session=False
        )
        db.commit()

    consultorio = assert_created(
        client.post(
            "/api/consultorios",
            headers=auth_headers,
            json={
                "complejo_id": complejo["id"],
                "piso_id": piso["id"],
                "codigo": f"LEG-{suffix}",
                "nombre_visible": f"Consultorio Legacy {suffix}",
                "cluster_ids": [cluster["id"]],
            },
        )
    )
    medico = assert_created(
        client.post(
            "/api/medicos",
            headers=auth_headers,
            json={"nombre": "Médico", "apellidos": f"Legacy {suffix}", "nombre_visible": f"Dr. Legacy {suffix}"},
        )
    )
    paciente = assert_created(
        client.post(
            "/api/pacientes",
            headers=auth_headers,
            json={"nombre": "Paciente", "apellido_paterno": f"Legacy {suffix}", "celular": f"5558{suffix[:6]}"},
        )
    )
    appointment_at = datetime.now(ZoneInfo("America/Mexico_City")) + timedelta(minutes=60)
    cita = assert_created(
        client.post(
            "/api/citas",
            headers=auth_headers,
            json={
                "tipo": "PROGRAMADA",
                "paciente_id": paciente["id"],
                "medico_id": medico["id"],
                "consultorio_id": consultorio["id"],
                "complejo_id": complejo["id"],
                "piso_id": piso["id"],
                "fecha_cita": appointment_at.date().isoformat(),
                "hora_cita": appointment_at.time().replace(second=0, microsecond=0).isoformat(timespec="minutes"),
                "origen": "TEST",
            },
        )
    )
    llamado = assert_created(client.post(f"/api/citas/{cita['id']}/llamar", headers=auth_headers))
    assert llamado["consultorio"] == consultorio["nombre_visible"]

    public_response = client.get(f"/api/public-display/display-legacy-{suffix}/turnos")
    assert public_response.status_code == 200, public_response.text
    assert public_response.json()["turnos"][0]["turno"] == llamado["turno"]


def test_patient_appointment_qr_checkin_ticket_flow(client: TestClient, auth_headers: dict[str, str]) -> None:
    suffix = uuid4().hex[:8]

    institucion = assert_created(
        client.post(
            "/api/instituciones",
            headers=auth_headers,
            json={"nombre": f"Institución Flujo {suffix}", "razon_social": f"Institución Flujo {suffix} S.A."},
        )
    )
    complejo = assert_created(
        client.post(
            "/api/complejos",
            headers=auth_headers,
            json={
                "institucion_id": institucion["id"],
                "nombre": f"Torre Flujo {suffix}",
                "zona_horaria": "America/Mexico_City",
            },
        )
    )
    torre = assert_created(
        client.post(
            "/api/torres",
            headers=auth_headers,
            json={"complejo_id": complejo["id"], "nombre": f"Torre Flujo {suffix}", "numero_pisos": 20},
        )
    )
    pisos_response = client.get("/api/pisos", headers=auth_headers)
    assert pisos_response.status_code == 200, pisos_response.text
    piso = next(item for item in pisos_response.json() if item["torre_id"] == torre["id"] and item["numero"] == 1)
    piso_response = client.patch(
        f"/api/pisos/{piso['id']}",
        headers=auth_headers,
        json={"codigo": f"F-{suffix}", "nombre_visible": f"Piso Flujo {suffix}"},
    )
    assert piso_response.status_code == 200, piso_response.text
    piso = piso_response.json()
    cluster = assert_created(
        client.post(
            "/api/clusters-turnos",
            headers=auth_headers,
            json={"complejo_id": complejo["id"], "piso_id": piso["id"], "nombre": f"Cluster Flujo {suffix}"},
        )
    )
    assert_created(
        client.post(
            "/api/pantallas-turnos",
            headers=auth_headers,
            json={
                "codigo_dispositivo": f"display-flujo-{suffix}",
                "nombre": f"Pantalla Flujo {suffix}",
                "complejo_id": complejo["id"],
                "piso_id": piso["id"],
                "cluster_ids": [cluster["id"]],
            },
        )
    )
    consultorio = assert_created(
        client.post(
            "/api/consultorios",
            headers=auth_headers,
            json={
                "complejo_id": complejo["id"],
                "piso_id": piso["id"],
                "codigo": f"CF-{suffix}",
                "nombre_visible": f"Consultorio Flujo {suffix}",
                "cluster_ids": [cluster["id"]],
            },
        )
    )
    medico = assert_created(
        client.post(
            "/api/medicos",
            headers=auth_headers,
            json={"nombre": "Médico", "apellidos": f"Flujo {suffix}", "nombre_visible": f"Dr. Flujo {suffix}"},
        )
    )

    paciente = assert_created(
        client.post(
            "/api/pacientes",
            headers=auth_headers,
            json={
                "nombre": "Flujo",
                "nombre_preferido": f"Alias {suffix}",
                "apellido_paterno": f"Paciente {suffix}",
                "celular": f"5559{suffix[:6]}",
            },
        )
    )
    search_response = client.get("/api/pacientes/buscar", headers=auth_headers, params={"q": paciente["folio_paciente"]})
    assert search_response.status_code == 200, search_response.text
    assert search_response.json()[0]["id"] == paciente["id"]

    appointment_at = datetime.now(ZoneInfo("America/Mexico_City")) + timedelta(minutes=60)
    payload = {
        "tipo": "PROGRAMADA",
        "paciente_id": paciente["id"],
        "medico_id": medico["id"],
        "consultorio_id": consultorio["id"],
        "complejo_id": complejo["id"],
        "piso_id": piso["id"],
        "fecha_cita": appointment_at.date().isoformat(),
        "hora_cita": appointment_at.time().replace(second=0, microsecond=0).isoformat(timespec="minutes"),
        "origen": "TEST",
    }
    cita = assert_created(client.post("/api/citas", headers=auth_headers, json=payload))
    assert is_valid_turn_folio(cita["folio_turno"])
    assert all(char in FOLIO_TURNO_ALPHABET for char in cita["folio_turno"])

    kiosk_search_response = client.get(
        "/api/citas/buscar",
        params={"paciente": f"Alias {suffix}", "fecha": appointment_at.date().isoformat()},
    )
    assert kiosk_search_response.status_code == 200, kiosk_search_response.text
    kiosk_matches = kiosk_search_response.json()
    assert any(item["id"] == cita["id"] for item in kiosk_matches)

    citas_response = client.get(
        "/api/citas",
        headers=auth_headers,
        params={"fecha": appointment_at.date().isoformat(), "paciente": f"Alias {suffix}"},
    )
    assert citas_response.status_code == 200, citas_response.text
    cita_item = next(item for item in citas_response.json() if item["id"] == cita["id"])
    assert cita_item["paciente"] == f"Alias {suffix}"
    assert cita_item["paciente_nombre_completo"] == f"Alias {suffix} (Flujo Paciente {suffix})"

    duplicate_response = client.post("/api/citas", headers=auth_headers, json=payload)
    assert duplicate_response.status_code == 409

    espontanea_payload = {**payload, "tipo": "ESPONTANEA", "hora_cita": (appointment_at + timedelta(minutes=30)).time().replace(second=0, microsecond=0).isoformat(timespec="minutes")}
    espontanea = assert_created(client.post("/api/citas?confirmar_duplicado=true", headers=auth_headers, json=espontanea_payload))
    assert espontanea["tipo"] == "ESPONTANEA"

    qr_response = assert_created(client.post(f"/api/citas/{cita['id']}/qr", headers=auth_headers))
    token = qr_response["qr_payload"]
    assert paciente["nombre"] not in token
    assert consultorio["codigo"] not in token

    validar_response = client.post("/api/qr/validar", json={"token": token})
    assert validar_response.status_code == 200, validar_response.text
    assert validar_response.json()["valido"] is True

    ticket_response = client.get(f"/api/citas/{cita['id']}/ticket", headers=auth_headers)
    assert ticket_response.status_code == 200, ticket_response.text
    ticket = ticket_response.json()
    assert ticket["turno"] == cita["folio_turno"]
    assert ticket["torre"] == torre["nombre"]
    assert ticket["piso"] == piso["nombre_visible"]
    assert ticket["qr_payload"]

    roles_response = client.get("/api/roles", headers=auth_headers)
    assert roles_response.status_code == 200, roles_response.text
    recepcionista_role = next(role for role in roles_response.json() if role["codigo"] == "RECEPCIONISTA")
    recepcionista_user = assert_created(
        client.post(
            "/api/usuarios",
            headers=auth_headers,
            json={
                "apellidos": f"Mobile {suffix}",
                "nombre": f"Recepcionista Mobile {suffix}",
                "email": f"recepcion-mobile-{suffix}@example.com",
                "password": "Temporal123!",
            },
        )
    )
    assert_created(
        client.post(
            "/api/usuario-roles",
            headers=auth_headers,
            json={
                "usuario_id": recepcionista_user["id"],
                "rol_id": recepcionista_role["id"],
                "institucion_id": institucion["id"],
                "complejo_id": complejo["id"],
            },
        )
    )
    recepcionista_login = client.post(
        "/api/auth/login",
        json={"email": recepcionista_user["email"], "password": "Temporal123!"},
    )
    assert recepcionista_login.status_code == 200, recepcionista_login.text
    recepcionista_headers = {"Authorization": f"Bearer {recepcionista_login.json()['access_token']}"}

    mobile_session = client.get("/api/mobile/session", headers=recepcionista_headers)
    assert mobile_session.status_code == 200, mobile_session.text
    assert mobile_session.json()["can_checkin"] is True
    assert mobile_session.json()["can_view_logs"] is False

    open_search = client.get("/api/mobile/citas/buscar", params={"paciente": f"Alias {suffix}", "celular": paciente["celular"]})
    assert open_search.status_code == 401, open_search.text

    incomplete_search = client.get("/api/mobile/citas/buscar", headers=recepcionista_headers, params={"paciente": f"Alias {suffix}"})
    assert incomplete_search.status_code == 422, incomplete_search.text

    mobile_search = client.get(
        "/api/mobile/citas/buscar",
        headers=recepcionista_headers,
        params={
            "paciente": f"Alias {suffix}",
            "celular": paciente["celular"],
            "fecha": appointment_at.date().isoformat(),
        },
    )
    assert mobile_search.status_code == 200, mobile_search.text
    assert any(item["id"] == cita["id"] for item in mobile_search.json())

    mobile_ticket_response = client.get(f"/api/mobile/citas/{cita['id']}/ticket", headers=recepcionista_headers)
    assert mobile_ticket_response.status_code == 200, mobile_ticket_response.text
    assert mobile_ticket_response.json()["turno"] == cita["folio_turno"]
    assert mobile_ticket_response.json()["torre"] == torre["nombre"]

    checkin_response = client.post(
        "/api/mobile/qr/checkin",
        headers=recepcionista_headers,
        json={"token": token, "canal": "APP_MOVIL", "dispositivo_id": "android-test"},
    )
    assert checkin_response.status_code == 200, checkin_response.text
    assert checkin_response.json()["resultado"] == "VERDE"
    assert checkin_response.json()["estado_cita"] == "LLEGO_LOBBY"

    audit_response = client.get("/api/auditoria", headers=auth_headers)
    audit_items = audit_response.json()
    events = {item["evento"] for item in audit_items}
    assert {"PACIENTE_CREADO", "CITA_CREADA", "QR_GENERADO", "QR_VALIDADO", "CHECKIN_LOBBY"}.issubset(events)
    assert any(
        item["evento"] == "CHECKIN_LOBBY"
        and item["usuario_id"] == recepcionista_user["id"]
        and item["canal"] == "APP_MOVIL"
        and item["valor_despues"]["cita_id"] == cita["id"]
        for item in audit_items
    )
