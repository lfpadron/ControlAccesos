from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.flow import query_citas, validate_patient_contact
from app.api.kiosks import patient_matches_contact, patient_phone_display
from app.models.flow import Paciente
from app.schemas.flow import PacienteCreate, PacienteRead, PacienteUpdate, metodos_confirmacion_disponibles


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


@pytest.mark.parametrize("phone_type", [None, "", "   "])
def test_patient_can_save_and_clear_second_phone_type_without_number(phone_type) -> None:
    engine = create_engine("sqlite://")
    Paciente.__table__.create(engine)
    payload = PacienteCreate(**(patient_payload() | {"celular": None, "tipo_telefono_2": phone_type}))

    with Session(engine) as db:
        patient = Paciente(**payload.model_dump(exclude={"medico_id"}), folio_paciente="PTEST")
        db.add(patient)
        db.commit()
        db.refresh(patient)
        assert PacienteRead.model_validate(patient).tipo_telefono_2 is None
        assert patient.celular is None

        patient.tipo_telefono_2 = "FIJO"
        db.commit()
        update = PacienteUpdate(tipo_telefono_2=phone_type)
        for key, value in update.model_dump(exclude_unset=True).items():
            setattr(patient, key, value)
        db.commit()
        db.refresh(patient)
        assert PacienteRead.model_validate(patient).tipo_telefono_2 is None

    engine.dispose()


@pytest.mark.parametrize("phone_type", [None, "", "   "])
def test_patient_cannot_create_second_phone_without_type(phone_type) -> None:
    with pytest.raises(ValidationError, match="Selecciona Fijo o Celular para Teléfono 2"):
        PacienteCreate(**(patient_payload() | {"tipo_telefono_2": phone_type}))


@pytest.mark.parametrize("phone_type", ["FIJO", "CELULAR"])
def test_patient_can_create_second_phone_with_valid_type(phone_type) -> None:
    payload = PacienteCreate(**(patient_payload() | {"tipo_telefono_2": phone_type}))
    patient = Paciente(**payload.model_dump(exclude={"medico_id"}), folio_paciente="PTEST")
    validate_patient_contact(patient)
    assert patient.tipo_telefono_2 == phone_type


def test_confirmation_methods_skip_second_phone_without_type() -> None:
    assert metodos_confirmacion_disponibles("5512345678", "FIJO", "5598765432", None, None) == {
        "LLAMAR_FIJO_1"
    }
    with pytest.raises(ValidationError, match="no corresponde a los datos de contacto"):
        PacienteCreate(**(patient_payload() | {"tipo_telefono_2": None, "metodo_confirmacion": "WHATSAPP_2"}))


@pytest.mark.parametrize("second_phone", [{}, {"celular": None}, {"celular": ""}, {"celular": "   "}])
def test_patient_can_save_and_clear_second_phone_without_birth_date(second_phone) -> None:
    engine = create_engine("sqlite://")
    Paciente.__table__.create(engine)
    data = patient_payload()
    data.pop("celular")
    payload = PacienteCreate(**(data | second_phone))

    with Session(engine) as db:
        patient = Paciente(**payload.model_dump(exclude={"medico_id"}), folio_paciente="PTEST")
        validate_patient_contact(patient)
        db.add(patient)
        db.commit()
        db.refresh(patient)
        assert PacienteRead.model_validate(patient).celular is None
        assert patient.fecha_nacimiento is None

        patient.celular = "55 9876 5432"
        db.commit()
        update = PacienteUpdate(celular=second_phone.get("celular"))
        for key, value in update.model_dump(exclude_unset=True).items():
            setattr(patient, key, value)
        validate_patient_contact(patient)
        db.commit()
        db.refresh(patient)
        assert PacienteRead.model_validate(patient).celular is None
        assert patient.telefono_1 == "55 1234 5678"

    engine.dispose()


def test_patient_requires_first_phone_and_valid_email() -> None:
    missing_phone = patient_payload()
    missing_phone.pop("telefono_1")
    with pytest.raises(ValidationError, match="Teléfono 1 es obligatorio"):
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
