from __future__ import annotations

import os
from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app.main import app
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
    piso = assert_created(
        client.post(
            "/api/pisos",
            headers=auth_headers,
            json={
                "complejo_id": complejo["id"],
                "numero": f"T-{suffix}",
                "nombre_visible": f"Piso Test {suffix}",
            },
        )
    )
    update_response = client.patch(
        f"/api/pisos/{piso['id']}",
        headers=auth_headers,
        json={"descripcion": "Actualizado por prueba automatizada."},
    )
    assert update_response.status_code == 200, update_response.text

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

    consultorio = assert_created(
        client.post(
            "/api/consultorios",
            headers=auth_headers,
            json={
                "complejo_id": complejo["id"],
                "piso_id": piso["id"],
                "codigo": f"C-{suffix}",
                "nombre_visible": f"Consultorio Test {suffix}",
                "cluster_ids": [cluster["id"]],
            },
        )
    )

    medico_user = assert_created(
        client.post(
            "/api/usuarios",
            headers=auth_headers,
            json={
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
    piso = assert_created(
        client.post(
            "/api/pisos",
            headers=auth_headers,
            json={"complejo_id": complejo["id"], "numero": f"F-{suffix}", "nombre_visible": f"Piso Flujo {suffix}"},
        )
    )
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
    assert ticket["qr_payload"]

    checkin_response = client.post("/api/qr/checkin", json={"token": token, "canal": "KIOSKO"})
    assert checkin_response.status_code == 200, checkin_response.text
    assert checkin_response.json()["resultado"] == "VERDE"
    assert checkin_response.json()["estado_cita"] == "LLEGO_LOBBY"

    audit_response = client.get("/api/auditoria", headers=auth_headers)
    events = {item["evento"] for item in audit_response.json()}
    assert {"PACIENTE_CREADO", "CITA_CREADA", "QR_GENERADO", "QR_VALIDADO", "CHECKIN_LOBBY"}.issubset(events)
