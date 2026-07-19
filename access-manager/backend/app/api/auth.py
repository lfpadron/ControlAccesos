from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, get_current_user, hash_password, verify_password
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequest, PasswordChangeRequest, TokenResponse
from app.schemas.usuario import UsuarioRead
from app.services.audit_service import record_audit_event

router = APIRouter()


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
def me(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    return current_user


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
    return current_user
