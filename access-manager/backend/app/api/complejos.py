from __future__ import annotations

from uuid import UUID
from zoneinfo import available_timezones

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.complejo import Complejo
from app.models.institucion import Institucion
from app.models.usuario import Usuario
from app.schemas.complejo import ComplejoCreate, ComplejoRead, ComplejoUpdate
from app.services.audit_service import audit_safe_dict, record_audit_event

router = APIRouter()


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def exists_or_404(db: Session, item_id: UUID) -> Complejo:
    item = db.get(Complejo, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complejo no encontrado.")
    return item


def validate_institucion(db: Session, institucion_id: UUID) -> None:
    if db.get(Institucion, institucion_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institución no encontrada.")


@router.get("", response_model=list[ComplejoRead])
def list_complejos(
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
) -> list[Complejo]:
    return list(db.execute(select(Complejo).order_by(Complejo.nombre)).scalars())


@router.get("/zonas-horarias", response_model=list[str])
def list_zonas_horarias(
    _current_user: Usuario = Depends(get_current_user),
) -> list[str]:
    return sorted(available_timezones())


@router.post("", response_model=ComplejoRead, status_code=status.HTTP_201_CREATED)
def create_complejo(
    payload: ComplejoCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> Complejo:
    validate_institucion(db, payload.institucion_id)

    complejo = Complejo(**payload.model_dump())
    db.add(complejo)
    db.flush()
    record_audit_event(
        db,
        evento="complejo.creado",
        entidad="complejos",
        entidad_id=complejo.id,
        usuario_id=current_user.id,
        canal="api",
        ip_origen=client_ip(request),
        valor_despues={
            "id": str(complejo.id),
            "institucion_id": str(complejo.institucion_id),
            "nombre": complejo.nombre,
        },
    )
    db.commit()
    db.refresh(complejo)
    return complejo


@router.put("/{complejo_id}", response_model=ComplejoRead)
@router.patch("/{complejo_id}", response_model=ComplejoRead)
def update_complejo(
    complejo_id: UUID,
    payload: ComplejoUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> Complejo:
    complejo = exists_or_404(db, complejo_id)
    before = audit_safe_dict(complejo)
    data = payload.model_dump(exclude_unset=True)
    if data.get("institucion_id") is not None:
        validate_institucion(db, data["institucion_id"])
    for key, value in data.items():
        setattr(complejo, key, value)
    db.flush()
    record_audit_event(
        db,
        evento="complejo.editado",
        entidad="complejos",
        entidad_id=complejo.id,
        usuario_id=current_user.id,
        canal="api",
        ip_origen=client_ip(request),
        valor_antes=before,
        valor_despues=audit_safe_dict(complejo),
    )
    db.commit()
    db.refresh(complejo)
    return complejo


@router.post("/{complejo_id}/activar", response_model=ComplejoRead)
@router.patch("/{complejo_id}/activar", response_model=ComplejoRead)
def activar_complejo(
    complejo_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> Complejo:
    return set_complejo_active(complejo_id, True, request, db, current_user)


@router.post("/{complejo_id}/desactivar", response_model=ComplejoRead)
@router.patch("/{complejo_id}/desactivar", response_model=ComplejoRead)
def desactivar_complejo(
    complejo_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> Complejo:
    return set_complejo_active(complejo_id, False, request, db, current_user)


def set_complejo_active(
    complejo_id: UUID,
    active: bool,
    request: Request,
    db: Session,
    current_user: Usuario,
) -> Complejo:
    complejo = exists_or_404(db, complejo_id)
    before = audit_safe_dict(complejo)
    complejo.activo = active
    db.flush()
    record_audit_event(
        db,
        evento="complejo.editado",
        entidad="complejos",
        entidad_id=complejo.id,
        usuario_id=current_user.id,
        canal="api",
        ip_origen=client_ip(request),
        valor_antes=before,
        valor_despues=audit_safe_dict(complejo),
    )
    db.commit()
    db.refresh(complejo)
    return complejo
