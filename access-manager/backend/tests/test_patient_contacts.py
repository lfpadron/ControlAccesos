from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from app.api.flow import query_citas
from app.api.kiosks import patient_matches_contact, patient_phone_display
from app.schemas.flow import PacienteCreate, metodos_confirmacion_disponibles


def patient_payload() -> dict:
    return {
        "nombre": "Paciente",
        "apellido_paterno": "Prueba",
        "telefono_1": "55 1234 5678",
        "celular": "55 9876 5432",
        "medico_id": uuid4(),
    }


def test_patient_contact_defaults_preserve_second_phone_as_mobile() -> None:
    patient = PacienteCreate(**patient_payload())

    assert patient.tipo_telefono_1 == "FIJO"
    assert patient.tipo_telefono_2 == "CELULAR"
    assert patient.celular == "55 9876 5432"


def test_patient_requires_both_phones_and_valid_email() -> None:
    missing_phone = patient_payload()
    missing_phone.pop("telefono_1")
    with pytest.raises(ValidationError, match="Teléfono 1 y Teléfono 2 son obligatorios"):
        PacienteCreate(**missing_phone)

    invalid_email = patient_payload() | {"correo_electronico": "correo-invalido"}
    with pytest.raises(ValidationError):
        PacienteCreate(**invalid_email)


def test_confirmation_methods_follow_available_contact_data() -> None:
    methods = metodos_confirmacion_disponibles(
        "55 1111 2222",
        "CELULAR",
        "55 3333 4444",
        "CELULAR",
        "paciente@example.com",
    )

    assert methods == {
        "LLAMAR_CELULAR_1",
        "LLAMAR_CELULAR_2",
        "WHATSAPP_1",
        "WHATSAPP_2",
        "TELEGRAM_1",
        "TELEGRAM_2",
        "CORREO",
    }

    with pytest.raises(ValidationError, match="no corresponde a los datos de contacto"):
        PacienteCreate(**(patient_payload() | {"metodo_confirmacion": "WHATSAPP_1"}))


def test_kiosk_accepts_either_registered_phone() -> None:
    patient = SimpleNamespace(
        telefono_1="55 1234 5678",
        celular="55-9876-5432",
        fecha_nacimiento=date(1990, 1, 31),
    )

    assert patient_matches_contact(patient, "5512345678", None)
    assert patient_matches_contact(patient, "5598765432", None)
    assert not patient_matches_contact(patient, "5500000000", None)
    assert patient_phone_display(patient) == "XXX5678 / XXX5432"


def test_appointment_phone_search_uses_both_registered_phones() -> None:
    query = query_citas(SimpleNamespace(), celular="55 1234 5678")
    compiled = str(query.compile(dialect=postgresql.dialect()))

    assert "pacientes.telefono_1" in compiled
    assert "pacientes.celular" in compiled
