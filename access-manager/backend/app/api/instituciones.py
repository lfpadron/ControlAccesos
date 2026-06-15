from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.institucion import Institucion
from app.models.usuario import Usuario
from app.schemas.institucion import InstitucionCreate, InstitucionRead, InstitucionUpdate
from app.services.audit_service import audit_safe_dict, record_audit_event

router = APIRouter()


@router.get("", response_model=list[InstitucionRead])
def list_instituciones(
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
) -> list[Institucion]:
    query = select(Institucion)
    if q:
        term = f"%{q.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Institucion.nombre).like(term),
                func.lower(Institucion.razon_social).like(term),
            )
        )
    return list(db.execute(query.order_by(Institucion.nombre)).scalars())


@router.post("", response_model=InstitucionRead, status_code=status.HTTP_201_CREATED)
def create_institucion(
    payload: InstitucionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> Institucion:
    institucion = Institucion(**payload.model_dump())
    db.add(institucion)
    db.flush()
    record_audit_event(
        db,
        evento="INSTITUCION_CREADA",
        entidad="instituciones",
        entidad_id=institucion.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=request.client.host if request.client else None,
        valor_despues=audit_safe_dict(institucion),
    )
    db.commit()
    db.refresh(institucion)
    return institucion


def exists_or_404(db: Session, item_id: UUID) -> Institucion:
    item = db.get(Institucion, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institución no encontrada.")
    return item


@router.put("/{institucion_id}", response_model=InstitucionRead)
@router.patch("/{institucion_id}", response_model=InstitucionRead)
def update_institucion(
    institucion_id: UUID,
    payload: InstitucionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> Institucion:
    institucion = exists_or_404(db, institucion_id)
    before = audit_safe_dict(institucion)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(institucion, key, value)
    db.flush()
    record_audit_event(
        db,
        evento="INSTITUCION_EDITADA",
        entidad="instituciones",
        entidad_id=institucion.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=request.client.host if request.client else None,
        valor_antes=before,
        valor_despues=audit_safe_dict(institucion),
    )
    db.commit()
    db.refresh(institucion)
    return institucion


@router.post("/{institucion_id}/activar", response_model=InstitucionRead)
@router.patch("/{institucion_id}/activar", response_model=InstitucionRead)
def activar_institucion(
    institucion_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> Institucion:
    return set_active(institucion_id, True, request, db, current_user)


@router.post("/{institucion_id}/desactivar", response_model=InstitucionRead)
@router.patch("/{institucion_id}/desactivar", response_model=InstitucionRead)
def desactivar_institucion(
    institucion_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> Institucion:
    return set_active(institucion_id, False, request, db, current_user)


def set_active(institucion_id: UUID, active: bool, request: Request, db: Session, current_user: Usuario) -> Institucion:
    institucion = exists_or_404(db, institucion_id)
    before = audit_safe_dict(institucion)
    institucion.activo = active
    db.flush()
    record_audit_event(
        db,
        evento="INSTITUCION_EDITADA",
        entidad="instituciones",
        entidad_id=institucion.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=request.client.host if request.client else None,
        valor_antes=before,
        valor_despues=audit_safe_dict(institucion),
    )
    db.commit()
    db.refresh(institucion)
    return institucion
