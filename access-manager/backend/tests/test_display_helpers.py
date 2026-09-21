from types import SimpleNamespace
from uuid import uuid4

from app.api.display import next_appointment_consultorio_details
from app.models.operational import Piso, Torre


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
    assert next_appointment_consultorio_details(db, screen, other_tower) == ("Torre B", None)
