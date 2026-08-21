from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.complejo import Complejo
from app.models.contacto import ContactoInstitucional, ContactoInstitucionalComplejo, ContactoInstitucionalTorre
from app.models.institucion import Institucion
from app.models.operational import Torre
from app.models.usuario import Usuario
from app.schemas.contacto import (
    ContactoInstitucionalCatalogosRead,
    ContactoInstitucionalCreate,
    ContactoInstitucionalRead,
    ContactoInstitucionalUpdate,
)
from app.services.access_scope import (
    complejo_catalog_access_predicate,
    institucion_catalog_access_predicate,
    torre_catalog_access_predicate,
)
from app.services.audit_service import audit_safe_dict, record_audit_event

router = APIRouter()
AdminUser = Depends(require_role("ADMIN_SISTEMA", "ADMIN_NEGOCIO"))


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def exists_or_404(db: Session, item_id: UUID) -> ContactoInstitucional:
    item = db.get(ContactoInstitucional, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contacto institucional no encontrado.")
    return item


def validate_complexes(db: Session, complejo_ids: list[UUID]) -> None:
    if not complejo_ids:
        return
    found = set(db.execute(select(Complejo.id).where(Complejo.id.in_(complejo_ids))).scalars())
    missing = [str(item_id) for item_id in complejo_ids if item_id not in found]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Campus no encontrados: {', '.join(missing)}",
        )


def validate_torres(db: Session, torre_ids: list[UUID]) -> None:
    if not torre_ids:
        return
    found = set(db.execute(select(Torre.id).where(Torre.id.in_(torre_ids))).scalars())
    missing = [str(item_id) for item_id in torre_ids if item_id not in found]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Torres no encontradas: {', '.join(missing)}",
        )


def unique_uuid_list(values: list[UUID]) -> list[UUID]:
    unique: list[UUID] = []
    seen: set[UUID] = set()
    for value in values:
        if value in seen:
            continue
        unique.append(value)
        seen.add(value)
    return unique


def complex_ids_for(db: Session, contacto_id: UUID) -> list[UUID]:
    return list(
        db.execute(
            select(ContactoInstitucionalComplejo.complejo_id)
            .where(ContactoInstitucionalComplejo.contacto_id == contacto_id)
            .order_by(ContactoInstitucionalComplejo.complejo_id)
        ).scalars()
    )


def torre_ids_for(db: Session, contacto_id: UUID) -> list[UUID]:
    return list(
        db.execute(
            select(ContactoInstitucionalTorre.torre_id)
            .where(ContactoInstitucionalTorre.contacto_id == contacto_id)
            .order_by(ContactoInstitucionalTorre.torre_id)
        ).scalars()
    )


def response_for(db: Session, item: ContactoInstitucional) -> ContactoInstitucionalRead:
    return ContactoInstitucionalRead(
        id=item.id,
        nombre=item.nombre,
        medios_contacto=item.medios_contacto,
        tipo_contacto=item.tipo_contacto,
        tipo_contacto_descripcion=item.tipo_contacto_descripcion,
        notas=item.notas,
        complejo_ids=complex_ids_for(db, item.id),
        torre_ids=torre_ids_for(db, item.id),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def replace_complexes(db: Session, contacto_id: UUID, complejo_ids: list[UUID]) -> None:
    db.query(ContactoInstitucionalComplejo).filter(ContactoInstitucionalComplejo.contacto_id == contacto_id).delete()
    for complejo_id in unique_uuid_list(complejo_ids):
        db.add(ContactoInstitucionalComplejo(contacto_id=contacto_id, complejo_id=complejo_id))


def replace_torres(db: Session, contacto_id: UUID, torre_ids: list[UUID]) -> None:
    db.query(ContactoInstitucionalTorre).filter(ContactoInstitucionalTorre.contacto_id == contacto_id).delete()
    for torre_id in unique_uuid_list(torre_ids):
        db.add(ContactoInstitucionalTorre(contacto_id=contacto_id, torre_id=torre_id))


def no_location_scope_predicate():
    has_complex = (
        select(ContactoInstitucionalComplejo.contacto_id)
        .where(ContactoInstitucionalComplejo.contacto_id == ContactoInstitucional.id)
        .exists()
    )
    has_tower = (
        select(ContactoInstitucionalTorre.contacto_id)
        .where(ContactoInstitucionalTorre.contacto_id == ContactoInstitucional.id)
        .exists()
    )
    return and_(~has_complex, ~has_tower)


def contact_access_predicate(db: Session, user: Usuario, today: date):
    complex_access = (
        select(ContactoInstitucionalComplejo.contacto_id)
        .join(Complejo, Complejo.id == ContactoInstitucionalComplejo.complejo_id)
        .where(
            ContactoInstitucionalComplejo.contacto_id == ContactoInstitucional.id,
            complejo_catalog_access_predicate(db, user, today),
        )
        .exists()
    )
    tower_access = (
        select(ContactoInstitucionalTorre.contacto_id)
        .join(Torre, Torre.id == ContactoInstitucionalTorre.torre_id)
        .where(
            ContactoInstitucionalTorre.contacto_id == ContactoInstitucional.id,
            torre_catalog_access_predicate(db, user, today),
        )
        .exists()
    )
    return or_(no_location_scope_predicate(), complex_access, tower_access)


def contact_institution_predicate(institucion_id: UUID):
    complex_in_institution = (
        select(ContactoInstitucionalComplejo.contacto_id)
        .join(Complejo, Complejo.id == ContactoInstitucionalComplejo.complejo_id)
        .where(
            ContactoInstitucionalComplejo.contacto_id == ContactoInstitucional.id,
            Complejo.institucion_id == institucion_id,
        )
        .exists()
    )
    tower_in_institution = (
        select(ContactoInstitucionalTorre.contacto_id)
        .join(Torre, Torre.id == ContactoInstitucionalTorre.torre_id)
        .join(Complejo, Complejo.id == Torre.complejo_id)
        .where(
            ContactoInstitucionalTorre.contacto_id == ContactoInstitucional.id,
            Complejo.institucion_id == institucion_id,
        )
        .exists()
    )
    return or_(no_location_scope_predicate(), complex_in_institution, tower_in_institution)


def contact_complex_predicate(complejo_id: UUID):
    complex_match = (
        select(ContactoInstitucionalComplejo.contacto_id)
        .where(
            ContactoInstitucionalComplejo.contacto_id == ContactoInstitucional.id,
            ContactoInstitucionalComplejo.complejo_id == complejo_id,
        )
        .exists()
    )
    tower_in_complex = (
        select(ContactoInstitucionalTorre.contacto_id)
        .join(Torre, Torre.id == ContactoInstitucionalTorre.torre_id)
        .where(
            ContactoInstitucionalTorre.contacto_id == ContactoInstitucional.id,
            Torre.complejo_id == complejo_id,
        )
        .exists()
    )
    return or_(no_location_scope_predicate(), complex_match, tower_in_complex)


def contact_tower_predicate(torre_id: UUID):
    tower_parent_complex = select(Torre.complejo_id).where(Torre.id == torre_id).scalar_subquery()
    complex_parent_match = (
        select(ContactoInstitucionalComplejo.contacto_id)
        .where(
            ContactoInstitucionalComplejo.contacto_id == ContactoInstitucional.id,
            ContactoInstitucionalComplejo.complejo_id == tower_parent_complex,
        )
        .exists()
    )
    tower_match = (
        select(ContactoInstitucionalTorre.contacto_id)
        .where(
            ContactoInstitucionalTorre.contacto_id == ContactoInstitucional.id,
            ContactoInstitucionalTorre.torre_id == torre_id,
        )
        .exists()
    )
    return or_(no_location_scope_predicate(), complex_parent_match, tower_match)


def ensure_accessible_filters(
    db: Session,
    current_user: Usuario,
    today: date,
    institucion_id: UUID | None,
    complejo_id: UUID | None,
    torre_id: UUID | None,
) -> None:
    if institucion_id is not None:
        exists = (
            db.execute(
                select(Institucion.id)
                .where(
                    Institucion.id == institucion_id,
                    Institucion.activo.is_(True),
                    institucion_catalog_access_predicate(db, current_user, today),
                )
                .limit(1)
            ).first()
            is not None
        )
        if not exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institución no encontrada.")
    if complejo_id is not None:
        conditions = [
            Complejo.id == complejo_id,
            Complejo.activo.is_(True),
            complejo_catalog_access_predicate(db, current_user, today),
        ]
        if institucion_id is not None:
            conditions.append(Complejo.institucion_id == institucion_id)
        exists = db.execute(select(Complejo.id).where(*conditions).limit(1)).first() is not None
        if not exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campus no encontrado.")
    if torre_id is not None:
        query = select(Torre.id).join(Complejo, Complejo.id == Torre.complejo_id).where(
            Torre.id == torre_id,
            Torre.activo.is_(True),
            torre_catalog_access_predicate(db, current_user, today),
        )
        if complejo_id is not None:
            query = query.where(Torre.complejo_id == complejo_id)
        if institucion_id is not None:
            query = query.where(Complejo.institucion_id == institucion_id)
        if db.execute(query.limit(1)).first() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torre no encontrada.")


@router.get("/catalogos", response_model=ContactoInstitucionalCatalogosRead)
def list_catalogos_contactos(
    db: Session = Depends(get_db),
    current_user: Usuario = AdminUser,
) -> ContactoInstitucionalCatalogosRead:
    today = date.today()
    instituciones = list(
        db.execute(
            select(Institucion)
            .where(
                Institucion.activo.is_(True),
                institucion_catalog_access_predicate(db, current_user, today),
            )
            .order_by(func.lower(Institucion.nombre), Institucion.id)
        ).scalars()
    )
    complejos = list(
        db.execute(
            select(Complejo)
            .where(
                Complejo.activo.is_(True),
                complejo_catalog_access_predicate(db, current_user, today),
            )
            .order_by(func.lower(Complejo.nombre), Complejo.id)
        ).scalars()
    )
    torres = list(
        db.execute(
            select(Torre)
            .where(
                Torre.activo.is_(True),
                torre_catalog_access_predicate(db, current_user, today),
            )
            .order_by(Torre.complejo_id, func.lower(Torre.nombre), Torre.id)
        ).scalars()
    )
    return ContactoInstitucionalCatalogosRead(instituciones=instituciones, complejos=complejos, torres=torres)


@router.get("", response_model=list[ContactoInstitucionalRead])
def list_contactos(
    q: str | None = Query(default=None),
    institucion_id: UUID | None = Query(default=None),
    complejo_id: UUID | None = Query(default=None),
    torre_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Usuario = AdminUser,
) -> list[ContactoInstitucionalRead]:
    term = (q or "").strip().lower()
    if term and institucion_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Seleccione una institución para buscar contactos.",
        )
    today = date.today()
    ensure_accessible_filters(db, current_user, today, institucion_id, complejo_id, torre_id)
    query = select(ContactoInstitucional).where(contact_access_predicate(db, current_user, today))
    if institucion_id is not None:
        query = query.where(contact_institution_predicate(institucion_id))
    if complejo_id is not None:
        query = query.where(contact_complex_predicate(complejo_id))
    if torre_id is not None:
        query = query.where(contact_tower_predicate(torre_id))
    if term:
        like_term = f"%{term}%"
        query = query.where(
            or_(
                func.lower(ContactoInstitucional.nombre).like(like_term),
                func.lower(cast(ContactoInstitucional.medios_contacto, String)).like(like_term),
            )
        )
    items = db.execute(query.order_by(ContactoInstitucional.nombre)).scalars()
    return [response_for(db, item) for item in items]


@router.post("", response_model=ContactoInstitucionalRead, status_code=status.HTTP_201_CREATED)
def create_contacto(
    payload: ContactoInstitucionalCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = AdminUser,
) -> ContactoInstitucionalRead:
    validate_complexes(db, payload.complejo_ids)
    validate_torres(db, payload.torre_ids)
    item = ContactoInstitucional(
        nombre=payload.nombre,
        medios_contacto=[medio.model_dump() for medio in payload.medios_contacto],
        tipo_contacto=payload.tipo_contacto,
        tipo_contacto_descripcion=payload.tipo_contacto_descripcion.strip()
        if payload.tipo_contacto == "OTRO" and payload.tipo_contacto_descripcion
        else None,
        notas=payload.notas,
    )
    db.add(item)
    db.flush()
    replace_complexes(db, item.id, payload.complejo_ids)
    replace_torres(db, item.id, payload.torre_ids)
    record_audit_event(
        db,
        evento="CONTACTO_INSTITUCIONAL_CREADO",
        entidad="contactos_institucionales",
        entidad_id=item.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_despues={
            **audit_safe_dict(item),
            "complejo_ids": [str(item_id) for item_id in payload.complejo_ids],
            "torre_ids": [str(item_id) for item_id in payload.torre_ids],
        },
    )
    db.commit()
    db.refresh(item)
    return response_for(db, item)


@router.put("/{contacto_id}", response_model=ContactoInstitucionalRead)
@router.patch("/{contacto_id}", response_model=ContactoInstitucionalRead)
def update_contacto(
    contacto_id: UUID,
    payload: ContactoInstitucionalUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = AdminUser,
) -> ContactoInstitucionalRead:
    item = exists_or_404(db, contacto_id)
    before = {
        **audit_safe_dict(item),
        "complejo_ids": [str(item_id) for item_id in complex_ids_for(db, item.id)],
        "torre_ids": [str(item_id) for item_id in torre_ids_for(db, item.id)],
    }
    data = payload.model_dump(exclude_unset=True)
    complejo_ids = data.pop("complejo_ids", None)
    torre_ids = data.pop("torre_ids", None)
    if "medios_contacto" in data and data["medios_contacto"] is not None:
        data["medios_contacto"] = [medio.model_dump() for medio in payload.medios_contacto or []]
    if "tipo_contacto_descripcion" in data and data["tipo_contacto_descripcion"]:
        data["tipo_contacto_descripcion"] = data["tipo_contacto_descripcion"].strip()
    if data.get("tipo_contacto") and data["tipo_contacto"] != "OTRO":
        data["tipo_contacto_descripcion"] = None
    for key, value in data.items():
        setattr(item, key, value)
    if complejo_ids is not None:
        validate_complexes(db, complejo_ids)
        replace_complexes(db, item.id, complejo_ids)
    if torre_ids is not None:
        validate_torres(db, torre_ids)
        replace_torres(db, item.id, torre_ids)
    db.flush()
    record_audit_event(
        db,
        evento="CONTACTO_INSTITUCIONAL_EDITADO",
        entidad="contactos_institucionales",
        entidad_id=item.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_antes=before,
        valor_despues={
            **audit_safe_dict(item),
            "complejo_ids": [str(item_id) for item_id in complex_ids_for(db, item.id)],
            "torre_ids": [str(item_id) for item_id in torre_ids_for(db, item.id)],
        },
    )
    db.commit()
    db.refresh(item)
    return response_for(db, item)
