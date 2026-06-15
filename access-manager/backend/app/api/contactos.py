from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.complejo import Complejo
from app.models.contacto import ContactoInstitucional, ContactoInstitucionalComplejo
from app.models.usuario import Usuario
from app.schemas.contacto import ContactoInstitucionalCreate, ContactoInstitucionalRead, ContactoInstitucionalUpdate
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Complejos no encontrados: {', '.join(missing)}")


def complex_ids_for(db: Session, contacto_id: UUID) -> list[UUID]:
    return list(
        db.execute(
            select(ContactoInstitucionalComplejo.complejo_id).where(ContactoInstitucionalComplejo.contacto_id == contacto_id)
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
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def replace_complexes(db: Session, contacto_id: UUID, complejo_ids: list[UUID]) -> None:
    db.query(ContactoInstitucionalComplejo).filter(ContactoInstitucionalComplejo.contacto_id == contacto_id).delete()
    for complejo_id in complejo_ids:
        db.add(ContactoInstitucionalComplejo(contacto_id=contacto_id, complejo_id=complejo_id))


@router.get("", response_model=list[ContactoInstitucionalRead])
def list_contactos(
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _current_user: Usuario = AdminUser,
) -> list[ContactoInstitucionalRead]:
    query = select(ContactoInstitucional)
    if q:
        query = query.where(func.lower(ContactoInstitucional.nombre).like(f"%{q.strip().lower()}%"))
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
    record_audit_event(
        db,
        evento="CONTACTO_INSTITUCIONAL_CREADO",
        entidad="contactos_institucionales",
        entidad_id=item.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_despues={**audit_safe_dict(item), "complejo_ids": [str(item_id) for item_id in payload.complejo_ids]},
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
    before = {**audit_safe_dict(item), "complejo_ids": [str(item_id) for item_id in complex_ids_for(db, item.id)]}
    data = payload.model_dump(exclude_unset=True)
    complejo_ids = data.pop("complejo_ids", None)
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
        valor_despues={**audit_safe_dict(item), "complejo_ids": [str(item_id) for item_id in complex_ids_for(db, item.id)]},
    )
    db.commit()
    db.refresh(item)
    return response_for(db, item)
