from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.operational import validate_clusters_for_scope
from app.models.complejo import Complejo


class FakeResult:
    def __init__(self, clusters=None, first=None):
        self._clusters = clusters or []
        self._first = first

    def scalars(self):
        return iter(self._clusters)

    def first(self):
        return self._first


class FakeSession:
    def __init__(self, clusters, campuses):
        self.clusters = clusters
        self.campuses = campuses
        self.execute_count = 0

    def get(self, model, item_id):
        if model is Complejo:
            return self.campuses.get(item_id)
        return None

    def execute(self, _query):
        self.execute_count += 1
        if self.execute_count == 1:
            return FakeResult(clusters=self.clusters)
        return FakeResult(first=object())


def test_consultorio_accepts_multiple_clusters_from_same_campus() -> None:
    institution_id = uuid4()
    campus_id = uuid4()
    clusters = [
        SimpleNamespace(id=uuid4(), complejo_id=campus_id, piso_id=uuid4()),
        SimpleNamespace(id=uuid4(), complejo_id=campus_id, piso_id=uuid4()),
    ]
    db = FakeSession(clusters, {campus_id: SimpleNamespace(id=campus_id, institucion_id=institution_id)})

    validate_clusters_for_scope(db, [cluster.id for cluster in clusters], campus_id)


def test_consultorio_rejects_cluster_from_another_campus_in_same_institution() -> None:
    institution_id = uuid4()
    consultorio_campus_id = uuid4()
    cluster_campus_id = uuid4()
    cluster = SimpleNamespace(id=uuid4(), complejo_id=cluster_campus_id, piso_id=uuid4())
    db = FakeSession(
        [cluster],
        {
            consultorio_campus_id: SimpleNamespace(id=consultorio_campus_id, institucion_id=institution_id),
            cluster_campus_id: SimpleNamespace(id=cluster_campus_id, institucion_id=institution_id),
        },
    )

    with pytest.raises(HTTPException) as exc_info:
        validate_clusters_for_scope(db, [cluster.id], consultorio_campus_id)
    assert exc_info.value.detail == "Los clústers y el consultorio deben pertenecer al mismo campus."


def test_consultorio_rejects_cluster_from_another_institution() -> None:
    consultorio_campus_id = uuid4()
    cluster_campus_id = uuid4()
    cluster = SimpleNamespace(id=uuid4(), complejo_id=cluster_campus_id, piso_id=uuid4())
    db = FakeSession(
        [cluster],
        {
            consultorio_campus_id: SimpleNamespace(id=consultorio_campus_id, institucion_id=uuid4()),
            cluster_campus_id: SimpleNamespace(id=cluster_campus_id, institucion_id=uuid4()),
        },
    )

    with pytest.raises(HTTPException) as exc_info:
        validate_clusters_for_scope(db, [cluster.id], consultorio_campus_id)
    assert exc_info.value.detail == "Los clústers y el consultorio deben pertenecer a la misma institución."
