from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.operational import Medico, Role, UsuarioRol
from app.models.usuario import Usuario


def sync_medicos_for_medico_users(db: Session, today: date | None = None, user_id: UUID | None = None) -> bool:
    effective_today = today or date.today()
    users_query = (
        select(Usuario)
        .join(UsuarioRol, UsuarioRol.usuario_id == Usuario.id)
        .join(Role, Role.id == UsuarioRol.rol_id)
        .where(
            Role.codigo == "MEDICO",
            Role.activo.is_(True),
            UsuarioRol.activo.is_(True),
            UsuarioRol.fecha_inicio <= effective_today,
            or_(UsuarioRol.fecha_fin.is_(None), UsuarioRol.fecha_fin >= effective_today),
            func.upper(Usuario.estado) == "ACTIVO",
        )
        .distinct()
    )
    if user_id is not None:
        users_query = users_query.where(Usuario.id == user_id)

    changed = False
    for user in db.execute(users_query).scalars().unique():
        medico = db.execute(
            select(Medico)
            .where(Medico.usuario_id == user.id)
            .order_by(Medico.activo.desc(), Medico.updated_at.desc(), Medico.id)
            .limit(1)
        ).scalar_one_or_none()
        if medico is None:
            db.add(Medico(usuario_id=user.id, nombre=user.nombre, apellidos=user.apellidos, activo=True))
            changed = True
            continue
        if medico.nombre != user.nombre:
            medico.nombre = user.nombre
            changed = True
        if medico.apellidos != user.apellidos:
            medico.apellidos = user.apellidos
            changed = True
        if not medico.activo:
            medico.activo = True
            changed = True

    if changed:
        db.flush()
    return changed
