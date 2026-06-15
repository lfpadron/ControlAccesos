from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, require_role
from app.models.complejo import Complejo
from app.models.kiosk import Kiosko, PuntoAcceso
from app.models.operational import Piso
from app.models.usuario import Usuario
from app.schemas.kiosk import KioskoCreate, KioskoRead, KioskoUpdate, PuntoAccesoCreate, PuntoAccesoRead, PuntoAccesoUpdate
from app.services.audit_service import audit_safe_dict, record_audit_event

router = APIRouter()
AdminUser = Depends(require_role("ADMIN_SISTEMA", "ADMIN_NEGOCIO"))


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def exists_or_404(db: Session, model: type, item_id: UUID, label: str) -> object:
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} no encontrado.")
    return item


def validate_scope(db: Session, data: dict, item: object | None = None) -> tuple[UUID | None, UUID | None]:
    complejo_id = data.get("complejo_id", getattr(item, "complejo_id", None))
    piso_id = data.get("piso_id", getattr(item, "piso_id", None))
    if complejo_id is not None:
        exists_or_404(db, Complejo, complejo_id, "Complejo")
    if piso_id is not None:
        piso = exists_or_404(db, Piso, piso_id, "Piso")
        if complejo_id is not None and piso.complejo_id != complejo_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El piso no pertenece al complejo indicado.")
    return complejo_id, piso_id


def validate_punto(db: Session, data: dict, item: PuntoAcceso | None = None) -> None:
    validate_scope(db, data, item)


def validate_kiosko(db: Session, data: dict, item: Kiosko | None = None) -> None:
    complejo_id, piso_id = validate_scope(db, data, item)
    punto_id = data.get("punto_acceso_id", getattr(item, "punto_acceso_id", None))
    if punto_id is not None:
        punto = exists_or_404(db, PuntoAcceso, punto_id, "Punto de acceso")
        if complejo_id is not None and punto.complejo_id != complejo_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El punto de acceso no pertenece al complejo indicado.")
        if piso_id is not None and punto.piso_id != piso_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El punto de acceso no pertenece al piso indicado.")
    codigo = data.get("codigo_dispositivo")
    if codigo is not None:
        query = select(Kiosko).where(Kiosko.codigo_dispositivo == codigo)
        if item is not None:
            query = query.where(Kiosko.id != item.id)
        if db.execute(query).scalar_one_or_none() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El código de dispositivo ya existe.")


def apply_kiosko_token(data: dict) -> dict:
    token = data.pop("token", None)
    if token:
        data["token_hash"] = hash_password(token)
    return data


@router.get("/puntos-acceso", response_model=list[PuntoAccesoRead])
def list_puntos_acceso(db: Session = Depends(get_db), _current_user: Usuario = AdminUser) -> list[PuntoAcceso]:
    return list(db.execute(select(PuntoAcceso).order_by(PuntoAcceso.nombre)).scalars())


@router.post("/puntos-acceso", response_model=PuntoAccesoRead, status_code=status.HTTP_201_CREATED)
def create_punto_acceso(
    payload: PuntoAccesoCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = AdminUser,
) -> PuntoAcceso:
    data = payload.model_dump()
    validate_punto(db, data)
    item = PuntoAcceso(**data)
    db.add(item)
    db.flush()
    record_audit_event(
        db,
        evento="PUNTO_ACCESO_CREADO",
        entidad="puntos_acceso",
        entidad_id=item.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_despues=audit_safe_dict(item),
    )
    db.commit()
    db.refresh(item)
    return item


@router.patch("/puntos-acceso/{item_id}", response_model=PuntoAccesoRead)
@router.put("/puntos-acceso/{item_id}", response_model=PuntoAccesoRead)
def update_punto_acceso(
    item_id: UUID,
    payload: PuntoAccesoUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = AdminUser,
) -> PuntoAcceso:
    item = exists_or_404(db, PuntoAcceso, item_id, "Punto de acceso")
    before = audit_safe_dict(item)
    data = payload.model_dump(exclude_unset=True)
    validate_punto(db, data, item)
    for key, value in data.items():
        setattr(item, key, value)
    db.flush()
    record_audit_event(
        db,
        evento="PUNTO_ACCESO_EDITADO",
        entidad="puntos_acceso",
        entidad_id=item.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_antes=before,
        valor_despues=audit_safe_dict(item),
    )
    db.commit()
    db.refresh(item)
    return item


@router.post("/puntos-acceso/{item_id}/activar", response_model=PuntoAccesoRead)
def activar_punto_acceso(item_id: UUID, request: Request, db: Session = Depends(get_db), current_user: Usuario = AdminUser) -> PuntoAcceso:
    return set_punto_acceso_active(item_id, True, request, db, current_user)


@router.post("/puntos-acceso/{item_id}/desactivar", response_model=PuntoAccesoRead)
def desactivar_punto_acceso(item_id: UUID, request: Request, db: Session = Depends(get_db), current_user: Usuario = AdminUser) -> PuntoAcceso:
    return set_punto_acceso_active(item_id, False, request, db, current_user)


def set_punto_acceso_active(item_id: UUID, active: bool, request: Request, db: Session, current_user: Usuario) -> PuntoAcceso:
    item = exists_or_404(db, PuntoAcceso, item_id, "Punto de acceso")
    before = audit_safe_dict(item)
    item.activo = active
    db.flush()
    record_audit_event(
        db,
        evento="PUNTO_ACCESO_EDITADO",
        entidad="puntos_acceso",
        entidad_id=item.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_antes=before,
        valor_despues=audit_safe_dict(item),
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/kioskos", response_model=list[KioskoRead])
def list_kioskos(db: Session = Depends(get_db), _current_user: Usuario = AdminUser) -> list[Kiosko]:
    return list(db.execute(select(Kiosko).order_by(Kiosko.codigo_dispositivo)).scalars())


@router.post("/kioskos", response_model=KioskoRead, status_code=status.HTTP_201_CREATED)
def create_kiosko(
    payload: KioskoCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = AdminUser,
) -> Kiosko:
    data = apply_kiosko_token(payload.model_dump())
    validate_kiosko(db, data)
    item = Kiosko(**data)
    db.add(item)
    db.flush()
    record_audit_event(
        db,
        evento="KIOSKO_CREADO",
        entidad="kioskos",
        entidad_id=item.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_despues=audit_safe_dict(item),
    )
    db.commit()
    db.refresh(item)
    return item


@router.patch("/kioskos/{item_id}", response_model=KioskoRead)
@router.put("/kioskos/{item_id}", response_model=KioskoRead)
def update_kiosko(
    item_id: UUID,
    payload: KioskoUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = AdminUser,
) -> Kiosko:
    item = exists_or_404(db, Kiosko, item_id, "Kiosko")
    before = audit_safe_dict(item)
    data = apply_kiosko_token(payload.model_dump(exclude_unset=True))
    validate_kiosko(db, data, item)
    for key, value in data.items():
        setattr(item, key, value)
    db.flush()
    record_audit_event(
        db,
        evento="KIOSKO_EDITADO",
        entidad="kioskos",
        entidad_id=item.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_antes=before,
        valor_despues=audit_safe_dict(item),
    )
    db.commit()
    db.refresh(item)
    return item


@router.post("/kioskos/{item_id}/activar", response_model=KioskoRead)
def activar_kiosko(item_id: UUID, request: Request, db: Session = Depends(get_db), current_user: Usuario = AdminUser) -> Kiosko:
    return set_kiosko_active(item_id, True, request, db, current_user)


@router.post("/kioskos/{item_id}/desactivar", response_model=KioskoRead)
def desactivar_kiosko(item_id: UUID, request: Request, db: Session = Depends(get_db), current_user: Usuario = AdminUser) -> Kiosko:
    return set_kiosko_active(item_id, False, request, db, current_user)


def set_kiosko_active(item_id: UUID, active: bool, request: Request, db: Session, current_user: Usuario) -> Kiosko:
    item = exists_or_404(db, Kiosko, item_id, "Kiosko")
    before = audit_safe_dict(item)
    item.activo = active
    db.flush()
    record_audit_event(
        db,
        evento="KIOSKO_EDITADO",
        entidad="kioskos",
        entidad_id=item.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_antes=before,
        valor_despues=audit_safe_dict(item),
    )
    db.commit()
    db.refresh(item)
    return item
