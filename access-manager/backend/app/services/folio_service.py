from __future__ import annotations

import secrets
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.flow import Cita, Paciente

FOLIO_TURNO_ALPHABET = "ACDEFGHJKMNPQRTWXY234679"
AMBIGUOUS_CHARS = set("IOBV108Ñ")


def random_code(length: int) -> str:
    return "".join(secrets.choice(FOLIO_TURNO_ALPHABET) for _ in range(length))


def generate_patient_folio(db: Session) -> str:
    for _ in range(30):
        folio = f"P{random_code(7)}"
        exists = db.execute(select(Paciente.id).where(Paciente.folio_paciente == folio)).scalar_one_or_none()
        if exists is None:
            return folio
    raise RuntimeError("No fue posible generar un folio de paciente único.")


def generate_turn_folio(db: Session, complejo_id: UUID, fecha_cita: date) -> str:
    for _ in range(60):
        folio = random_code(4)
        exists = db.execute(
            select(Cita.id).where(
                Cita.complejo_id == complejo_id,
                Cita.fecha_cita == fecha_cita,
                Cita.folio_turno == folio,
            )
        ).scalar_one_or_none()
        if exists is None:
            return folio
    raise RuntimeError("No fue posible generar un folio de turno único.")


def is_valid_turn_folio(folio: str) -> bool:
    return len(folio) == 4 and all(char in FOLIO_TURNO_ALPHABET and char not in AMBIGUOUS_CHARS for char in folio)
