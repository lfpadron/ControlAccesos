from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, get_current_user, hash_password, verify_password
from app.models.operational import Role, UsuarioRol
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequest, PasswordChangeRequest, TokenResponse
from app.schemas.usuario import UsuarioProfileUpdate, UsuarioRead
from app.services.audit_service import record_audit_event

router = APIRouter()


def normalize_profile_email(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    return normalized or None


def active_role_labels(db: Session, user: Usuario) -> list[str]:
    rows = db.execute(
        select(Role.nombre, Role.codigo)
        .join(UsuarioRol, UsuarioRol.rol_id == Role.id)
        .where(
            UsuarioRol.usuario_id == user.id,
            UsuarioRol.activo.is_(True),
            Role.activo.is_(True),
        )
        .order_by(Role.nombre, Role.codigo)
    ).all()
    labels: list[str] = []
    seen: set[str] = set()
    for nombre, codigo in rows:
        label = nombre or codigo
        if label not in seen:
            labels.append(label)
            seen.add(label)
    return labels


def user_read(db: Session, user: Usuario) -> UsuarioRead:
    return UsuarioRead.model_validate(user).model_copy(update={"roles": active_role_labels(db, user)})


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = str(payload.email).strip().lower()
    user = db.execute(select(Usuario).where(func.lower(Usuario.email) == email)).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
        )
    if user.estado != "ACTIVO":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo.",
        )
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UsuarioRead)
def me(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> UsuarioRead:
    return user_read(db, current_user)


@router.patch("/me", response_model=UsuarioRead)
def update_profile(
    payload: UsuarioProfileUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> UsuarioRead:
    before = {"correo_alterno": current_user.correo_alterno}
    current_user.correo_alterno = normalize_profile_email(payload.correo_alterno)
    db.flush()
    record_audit_event(
        db,
        evento="PERFIL_ACTUALIZADO",
        entidad="usuarios",
        entidad_id=current_user.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=request.client.host if request.client else None,
        valor_antes=before,
        valor_despues={"correo_alterno": current_user.correo_alterno},
    )
    db.commit()
    db.refresh(current_user)
    return user_read(db, current_user)


@router.post("/password", response_model=UsuarioRead)
def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La contraseña actual no es correcta.",
        )
    current_user.password_hash = hash_password(payload.new_password)
    current_user.force_password_change = False
    db.flush()
    record_audit_event(
        db,
        evento="PASSWORD_CAMBIADO",
        entidad="usuarios",
        entidad_id=current_user.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=request.client.host if request.client else None,
        valor_despues={"force_password_change": False},
    )
    db.commit()
    db.refresh(current_user)
    return user_read(db, current_user)
