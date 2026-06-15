from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, get_current_user, verify_password
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.usuario import UsuarioRead

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.execute(select(Usuario).where(Usuario.email == payload.email)).scalar_one_or_none()
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
