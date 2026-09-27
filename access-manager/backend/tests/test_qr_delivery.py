from datetime import UTC, date, datetime, time, timedelta
from io import BytesIO
import base64
import re
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api import flow, qr_delivery as api
from app.core.config import Settings
from app.core.database import get_db
from app.models.flow import Cita, Paciente, QrToken
from app.schemas.flow import PacienteUpdate
from app.services import qr_delivery as delivery
from app.services.qr_service import decode_qr_payload, get_active_qr_payload, token_digest


@pytest.fixture()
def settings(monkeypatch):
    value = Settings(_env_file=None, RESEND_API_KEY="test-resend-secret", QR_EMAIL_FROM="CMC <citas@example.com>",
                     TELEGRAM_BOT_TOKEN="test-bot-secret", TELEGRAM_BOT_USERNAME="cmc_test_bot",
                     TELEGRAM_WEBHOOK_SECRET="test-webhook-secret")
    monkeypatch.setattr(api, "get_settings", lambda: value)
    monkeypatch.setattr(delivery, "get_settings", lambda: value)
    return value


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    @event.listens_for(engine, "connect")
    def functions(connection, _):
        connection.create_function("regexp_replace", 4, lambda value, pattern, replacement, flags: re.sub(pattern, replacement, value) if value else value)
    for table in (Paciente.__table__, Cita.__table__, QrToken.__table__):
        table.create(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture()
def appointment(db):
    patient = Paciente(id=uuid4(), folio_paciente="PTESTQR", nombre_preferido="Paciente de prueba",
                       telefono_1="55 1234 5678", tipo_telefono_1="CELULAR",
                       celular="+52 55 9876 5678", tipo_telefono_2="CELULAR",
                       correo_electronico="patient@example.com", metodo_confirmacion="CORREO",
                       telegram_chat_id_1=12345, telegram_chat_id_2=67890)
    cita = Cita(id=uuid4(), paciente_id=patient.id, tipo="PROGRAMADA", estado="AGENDADA",
                medico_id=uuid4(), consultorio_id=uuid4(), complejo_id=uuid4(), piso_id=uuid4(),
                fecha_cita=date.today() + timedelta(days=2), hora_cita=time(10, 30), folio_turno="A123")
    db.add_all([patient, cita])
    db.commit()
    return cita, patient


@pytest.fixture()
def client(monkeypatch, db, settings):
    app = FastAPI()
    app.include_router(api.router, prefix="/api")
    def database():
        yield db
    app.dependency_overrides[get_db] = database
    user = SimpleNamespace(id=uuid4())
    for permission in (api.CitasOperationalReadUser, api.CitasOperationalWriteUser, api.PacientesReadUser, api.PacientesWriteUser):
        app.dependency_overrides[permission.dependency] = lambda: user
    monkeypatch.setattr(api, "ensure_cita_access", lambda *args: None)
    monkeypatch.setattr(api, "ensure_paciente_access", lambda *args: None)
    monkeypatch.setattr(delivery, "qr_details", lambda db, cita: ["Cita 27/09/2026 10:30", "Torre A", "Piso 1", "Consultorio con acentos: México"])
    with TestClient(app) as test_client:
        yield test_client


def preview(client, cita):
    response = client.post(f"/api/citas/{cita.id}/qr/preparar")
    assert response.status_code == 200, response.text
    return response.json()


def send_payload(data, method="CORREO"):
    return {"metodo": method, **{key: data[key] for key in ("qr_id", "cita_updated_at", "paciente_updated_at")}}


def test_previews_and_resends_preserve_token_and_png(client, db, appointment, monkeypatch):
    cita, patient = appointment
    first = preview(client, cita)
    second = preview(client, cita)
    assert first["qr_id"] == second["qr_id"]
    assert first["imagen_base64"] == second["imagen_base64"]
    assert len(db.scalars(select(QrToken)).all()) == 1
    calls = []
    monkeypatch.setattr(delivery, "send_email", lambda *args: calls.append(args))
    for _ in range(2):
        response = client.post(f"/api/citas/{cita.id}/qr/enviar", json=send_payload(second))
        assert response.status_code == 200, response.text
    assert len(calls) == 2
    assert calls[0][0] == patient.correo_electronico
    assert calls[0][1] == base64.b64decode(first["imagen_base64"])
    assert calls[0][2].endswith(".png")
    assert len(db.scalars(select(QrToken)).all()) == 1


def test_telegram_selects_full_registered_slot_despite_same_last_four(client, appointment, monkeypatch):
    cita, _ = appointment
    data = preview(client, cita)
    telegram = [item for item in data["destinos"] if item["metodo"].startswith("TELEGRAM")]
    assert len(telegram) == 2
    assert "Celular 1" in telegram[0]["etiqueta"] and "Celular 2" in telegram[1]["etiqueta"]
    assert all(item["etiqueta"].endswith("5678") for item in telegram)
    calls = []
    monkeypatch.setattr(delivery, "send_telegram", lambda *args: calls.append(args))
    response = client.post(f"/api/citas/{cita.id}/qr/enviar", json=send_payload(data, "TELEGRAM_2"))
    assert response.status_code == 200, response.text
    assert calls[0][0] == 67890


@pytest.mark.parametrize("state", ["CANCELADA", "EXPIRADA", "NO_LLEGO"])
def test_rejects_cancelled_or_invalid_appointment_after_preview(client, db, appointment, monkeypatch, state):
    cita, _ = appointment
    data = preview(client, cita)
    cita.estado = state
    db.commit()
    monkeypatch.setattr(delivery, "send_email", lambda *args: pytest.fail("Must not send"))
    response = client.post(f"/api/citas/{cita.id}/qr/enviar", json=send_payload(data))
    assert response.status_code == 409
    assert client.post(f"/api/citas/{cita.id}/qr/preparar").status_code == 409


@pytest.mark.parametrize("change", ["email", "appointment", "expired", "used", "wrong_qr"])
def test_rejects_stale_preview(client, db, appointment, monkeypatch, change):
    cita, patient = appointment
    data = preview(client, cita)
    qr = db.scalar(select(QrToken))
    if change == "email":
        patient.correo_electronico = "new@example.com"
        patient.updated_at = datetime.now(UTC) + timedelta(seconds=1)
    elif change == "appointment":
        cita.hora_cita = time(12, 30)
        cita.updated_at = datetime.now(UTC) + timedelta(seconds=1)
    elif change == "expired":
        qr.fecha_expiracion = datetime.now(UTC) - timedelta(seconds=1)
    elif change == "used":
        qr.estado = "USADO"
    else:
        data["qr_id"] = str(uuid4())
    db.commit()
    monkeypatch.setattr(delivery, "send_email", lambda *args: pytest.fail("Must not send"))
    assert client.post(f"/api/citas/{cita.id}/qr/enviar", json=send_payload(data)).status_code == 409


def test_scope_and_edit_permission_are_required(client, appointment, monkeypatch):
    cita, _ = appointment
    data = preview(client, cita)
    def deny(*args):
        raise HTTPException(403, "Sin acceso")
    monkeypatch.setattr(api, "ensure_cita_access", deny)
    assert client.post(f"/api/citas/{cita.id}/qr/preparar").status_code == 403
    assert client.post(f"/api/citas/{cita.id}/qr/enviar", json=send_payload(data)).status_code == 403
    monkeypatch.setattr(api, "ensure_cita_access", lambda *args: None)
    def no_edit():
        raise HTTPException(403, "Sin permiso de edición")
    client.app.dependency_overrides[api.CitasOperationalWriteUser.dependency] = no_edit
    assert client.post(f"/api/citas/{cita.id}/qr/enviar", json=send_payload(data)).status_code == 403


def test_no_arbitrary_recipient_or_unsupported_channel(client, appointment):
    cita, _ = appointment
    data = preview(client, cita)
    payload = send_payload(data)
    payload["to"] = "stranger@example.com"
    assert client.post(f"/api/citas/{cita.id}/qr/enviar", json=payload).status_code == 422
    assert client.post(f"/api/citas/{cita.id}/qr/enviar", json=send_payload(data, "WHATSAPP_1")).status_code == 422


def test_missing_contacts_and_configuration(appointment, settings):
    _, patient = appointment
    settings.resend_api_key = None
    patient.tipo_telefono_1 = "FIJO"
    patient.telegram_chat_id_2 = None
    options = delivery.destinations(patient)
    assert [item.metodo for item in options] == ["CORREO", "TELEGRAM_2"]
    assert not any(item.disponible for item in options)
    assert options[1].vinculable
    patient.correo_electronico = None
    patient.tipo_telefono_2 = "FIJO"
    assert delivery.destinations(patient) == []


def test_provider_error_is_reported_without_rotating_qr(client, db, appointment, monkeypatch):
    cita, _ = appointment
    data = preview(client, cita)
    def fail(*args):
        raise delivery.DeliveryError("Proveedor no disponible", 503)
    monkeypatch.setattr(delivery, "send_email", fail)
    response = client.post(f"/api/citas/{cita.id}/qr/enviar", json=send_payload(data))
    assert response.status_code == 503
    assert str(db.scalar(select(QrToken)).id) == data["qr_id"]


def telegram_update(chat=12345, phone="525512345678", owner=12345):
    return {"update_id": 1, "message": {"chat": {"id": chat, "type": "private"},
            "from": {"id": chat}, "contact": {"user_id": owner, "phone_number": phone}}}


def webhook(client, payload, secret="test-webhook-secret"):
    return client.post("/api/telegram/webhook", json=payload, headers={"X-Telegram-Bot-Api-Secret-Token": secret})


def test_telegram_requires_webhook_secret_and_own_contact(client, db, appointment, monkeypatch):
    _, patient = appointment
    patient.telegram_chat_id_1 = None
    db.commit()
    calls = []
    monkeypatch.setattr(delivery, "telegram_request", lambda *args, **kwargs: calls.append((args, kwargs)))
    assert webhook(client, telegram_update(), "wrong").status_code == 403
    assert not calls
    assert webhook(client, telegram_update(owner=999)).status_code == 200
    db.refresh(patient)
    assert patient.telegram_chat_id_1 is None
    assert webhook(client, telegram_update()).status_code == 200
    db.refresh(patient)
    assert patient.telegram_chat_id_1 == 12345
    assert patient.telegram_chat_id_2 == 67890


def test_bot_ignores_groups_and_links_matching_shared_family_contact(client, db, appointment, monkeypatch):
    _, patient = appointment
    relative = Paciente(id=uuid4(), folio_paciente="PFAMILY", nombre_preferido="Familiar",
                        celular="5512345678", tipo_telefono_2="CELULAR")
    db.add(relative)
    db.commit()
    monkeypatch.setattr(delivery, "telegram_request", lambda *args, **kwargs: {})
    update_payload = telegram_update()
    update_payload["message"]["chat"]["type"] = "group"
    assert webhook(client, update_payload).status_code == 200
    db.refresh(relative)
    assert relative.telegram_chat_id_2 is None
    assert webhook(client, telegram_update()).status_code == 200
    db.refresh(relative)
    assert relative.telegram_chat_id_2 == 12345
    assert webhook(client, {"message": {"chat": {"id": 12345, "type": "private"}, "from": {"id": 12345}, "text": "/stop"}}).status_code == 200
    db.refresh(patient)
    db.refresh(relative)
    assert patient.telegram_chat_id_1 is None and relative.telegram_chat_id_2 is None
    assert patient.telegram_chat_id_2 == 67890


def test_patient_can_unlink_one_slot(client, db, appointment):
    _, patient = appointment
    url = f"/api/pacientes/{patient.id}/telegram"
    response = client.delete(url + "/1")
    assert response.status_code == 200, response.text
    assert [item["vinculado"] for item in response.json()["contactos"]] == [False, True]
    assert "telegram_chat_id" not in response.text
    assert client.delete(url + "/3").status_code == 422


@pytest.mark.parametrize("changes, cleared", [({"telefono_1": "5511112222"}, 1), ({"celular": "5533334444"}, 2),
    ({"tipo_telefono_1": "FIJO"}, 1), ({"tipo_telefono_2": "FIJO"}, 2)])
def test_editing_phone_clears_only_its_telegram_link(db, appointment, monkeypatch, changes, cleared):
    from starlette.requests import Request
    _, patient = appointment
    monkeypatch.setattr(flow, "paciente_for_medico_or_404", lambda *args: patient)
    monkeypatch.setattr(flow, "ensure_paciente_access", lambda *args: None)
    monkeypatch.setattr(flow, "record_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(flow, "medico_ids_for_paciente", lambda *args: [])
    flow.update_paciente(patient.id, PacienteUpdate(**changes), Request({"type": "http", "headers": []}),
                         medico_id=uuid4(), db=db, current_user=SimpleNamespace(id=uuid4()))
    db.refresh(patient)
    assert getattr(patient, f"telegram_chat_id_{cleared}") is None
    assert getattr(patient, f"telegram_chat_id_{3 - cleared}") is not None


def test_start_requests_own_phone_and_inactive_patient_is_not_linked(client, db, appointment, monkeypatch):
    _, patient = appointment
    patient.telegram_chat_id_1 = None
    patient.activo = False
    db.commit()
    calls = []
    monkeypatch.setattr(delivery, "telegram_request", lambda method, **kwargs: calls.append((method, kwargs)))
    start = {"message": {"chat": {"id": 12345, "type": "private"}, "from": {"id": 12345}, "text": "/start cmc"}}
    assert webhook(client, start).status_code == 200
    assert calls[0][1]["json"]["reply_markup"]["keyboard"][0][0]["request_contact"] is True
    assert webhook(client, telegram_update()).status_code == 200
    db.refresh(patient)
    assert patient.telegram_chat_id_1 is None


def test_unconfigured_webhook_rejects_requests(client, settings, monkeypatch):
    settings.telegram_webhook_secret = None
    monkeypatch.setattr(delivery, "handle_telegram_update", lambda *args: pytest.fail("Must not handle update"))
    assert webhook(client, telegram_update()).status_code == 403


@pytest.mark.parametrize("raw, expected", [("55 1234 5678", "525512345678"), ("+52 (55) 1234-5678", "525512345678"),
    ("+5215512345678", "525512345678"), ("00525512345678", "525512345678"), ("+14155551234", "14155551234"),
    ("", None), ("1234", None), ("5512345678 ext 1", None)])
def test_phone_normalization(raw, expected):
    assert delivery.normalize_mobile(raw) == expected


def test_png_and_token_can_be_recreated_from_database(db, appointment):
    cita, _ = appointment
    qr, token = get_active_qr_payload(db, cita)
    db.commit()
    db.expire_all()
    second, again = get_active_qr_payload(db, cita)
    assert again == token and second.id == qr.id
    assert token_digest(token) == qr.token_hash
    assert decode_qr_payload(token)["cita_id"] == str(cita.id)
    png = delivery.render_qr_png(token, ["México — Clínica", "Nombre extenso " * 30])
    image = Image.open(BytesIO(png))
    assert image.format == "PNG" and image.width >= 640 and image.height > 640


def test_resend_and_telegram_https_payloads(settings, monkeypatch):
    requests = []
    def post(provider, url, **kwargs):
        requests.append((provider, url, kwargs))
        return {"id": "test-message", "ok": True}
    monkeypatch.setattr(delivery, "provider_post", post)
    delivery.send_email("patient@example.com", b"test-png", "qr.png", ["Cita 10:30"])
    payload = requests[0][2]["json"]
    assert requests[0][1] == "https://api.resend.com/emails"
    assert payload["to"] == ["patient@example.com"]
    assert base64.b64decode(payload["attachments"][0]["content"]) == b"test-png"
    delivery.send_telegram(67890, b"test-png", "qr.png", ["Cita 10:30"])
    assert requests[1][1].endswith("/sendDocument")
    assert requests[1][2]["data"]["chat_id"] == "67890"
    assert requests[1][2]["files"]["document"] == ("qr.png", b"test-png", "image/png")


@pytest.mark.parametrize("failure", ["timeout", "unauthorized", "rate_limit", "invalid_json"])
def test_provider_failures_never_expose_credentials(settings, monkeypatch, failure):
    class Client:
        def __init__(self, **kwargs):
            assert kwargs["timeout"] == 15
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, url, **kwargs):
            if failure == "timeout":
                raise httpx.ReadTimeout("sensitive-provider-url")
            return httpx.Response({"unauthorized": 401, "rate_limit": 429, "invalid_json": 200}[failure], text="sensitive-provider-body")
    monkeypatch.setattr(delivery.httpx, "Client", Client)
    with pytest.raises(delivery.DeliveryError) as raised:
        delivery.telegram_request("sendMessage", json={})
    assert "sensitive" not in str(raised.value)
    assert "test-bot-secret" not in str(raised.value)
    assert raised.value.status_code == (429 if failure == "rate_limit" else 502)
