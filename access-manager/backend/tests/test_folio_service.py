from datetime import date
from uuid import uuid4

from app.services.folio_service import (
    FOLIO_TURNO_DIGITS,
    FOLIO_TURNO_LETTERS,
    generate_turn_folio,
    is_valid_turn_folio,
)


class EmptyResult:
    def scalar_one_or_none(self):
        return None


class EmptySession:
    def execute(self, _query):
        return EmptyResult()


def test_generated_turn_folio_uses_two_letters_then_two_digits() -> None:
    db = EmptySession()
    for _ in range(25):
        folio = generate_turn_folio(db, uuid4(), date(2026, 9, 20))
        assert is_valid_turn_folio(folio)
        assert all(character in FOLIO_TURNO_LETTERS for character in folio[:2])
        assert all(character in FOLIO_TURNO_DIGITS for character in folio[2:])


def test_turn_folio_rejects_other_position_patterns() -> None:
    assert not is_valid_turn_folio("22AA")
    assert not is_valid_turn_folio("A2C3")
    assert not is_valid_turn_folio("AA2")
