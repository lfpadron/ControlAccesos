from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
import uuid

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import default_permissions_for_role
from app.core.config import get_settings
from app.core.database import get_db
from app.models.usuario import Usuario

password_hasher = PasswordHasher()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
ACCESS_ORDER = {"sin": 0, "consultar": 1, "editar": 2}


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, plain_password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    expires_at = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {"sub": subject, "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def resolve_current_user_from_token(token: str, db: Session) -> Usuario:
    settings = get_settings()
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No fue posible validar la sesión.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        subject = payload.get("sub")
        if subject is None:
            raise credentials_error
        user_id = uuid.UUID(subject)
    except (JWTError, ValueError):
        raise credentials_error from None

    user = db.execute(select(Usuario).where(Usuario.id == user_id)).scalar_one_or_none()
    if user is None or user.estado != "ACTIVO":
        raise credentials_error
    return user


def ensure_password_is_current(request: Request, user: Usuario) -> None:
    if user.force_password_change and request.url.path not in {"/api/auth/me", "/api/auth/password"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debe cambiar su contraseña antes de continuar.",
        )


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    user = resolve_current_user_from_token(token, db)
    ensure_password_is_current(request, user)
    return user


def get_optional_current_user(
    request: Request,
    token: str | None = Depends(optional_oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario | None:
    if token is None:
        return None
    user = resolve_current_user_from_token(token, db)
    ensure_password_is_current(request, user)
    return user


def require_role(*allowed_roles: str, scope: str | None = None):
    def dependency(
        current_user: Usuario = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> Usuario:
        from app.models.operational import Role, UsuarioRol

        role_codes = set(allowed_roles)
        role_codes.add("ADMIN_SISTEMA")

        query = (
            select(Role.codigo)
            .join(UsuarioRol, UsuarioRol.rol_id == Role.id)
            .where(
                UsuarioRol.usuario_id == current_user.id,
                UsuarioRol.activo.is_(True),
                Role.activo.is_(True),
                Role.codigo.in_(role_codes),
            )
        )
        user_roles = set(db.execute(query).scalars())
        if "ADMIN_SISTEMA" in user_roles:
            return current_user

        if scope is not None:
            # TODO: aplicar filtros por institución/complejo contra el recurso solicitado.
            # Mientras no exista esa verificacion contextual, bloqueamos por defecto.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El alcance del rol no pudo verificarse.",
            )

        if user_roles.intersection(allowed_roles):
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para ejecutar esta operación.",
        )

    return dependency


def require_permission(*screen_keys: str, minimum: str = "consultar"):
    if minimum not in ACCESS_ORDER:
        raise ValueError("minimum debe ser 'sin', 'consultar' o 'editar'")

    def dependency(
        current_user: Usuario = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> Usuario:
        from app.models.operational import Role, UsuarioRol

        today = date.today()
        roles = list(
            db.execute(
                select(Role)
                .join(UsuarioRol, UsuarioRol.rol_id == Role.id)
                .where(
                    UsuarioRol.usuario_id == current_user.id,
                    UsuarioRol.activo.is_(True),
                    UsuarioRol.fecha_inicio <= today,
                    (UsuarioRol.fecha_fin.is_(None) | (UsuarioRol.fecha_fin >= today)),
                    Role.activo.is_(True),
                )
            ).scalars()
        )
        if any(role.codigo == "ADMIN_SISTEMA" for role in roles):
            return current_user

        required_level = ACCESS_ORDER[minimum]
        for role in roles:
            permissions = {**default_permissions_for_role(role.codigo), **(role.permisos or {})}
            for screen_key in screen_keys:
                access = permissions.get(screen_key, "sin")
                if ACCESS_ORDER.get(access, 0) >= required_level:
                    return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para ejecutar esta operación.",
        )

    return dependency


def require_rbac_scope(scope: str):
    def dependency(current_user: Usuario = Depends(require_role("ADMIN_SISTEMA", scope=scope))) -> Usuario:
        return current_user

    return dependency
