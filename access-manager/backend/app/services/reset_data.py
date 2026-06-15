from __future__ import annotations

import logging

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.core.security import hash_password
from app.models.auditoria import Auditoria
from app.models.complejo import Complejo
from app.models.contacto import ContactoInstitucional, ContactoInstitucionalComplejo
from app.models.display import PantallaTurnos, PantallaTurnosCluster, TurnoDisplay
from app.models.flow import Cita, EventoLlegada, Paciente, QrToken
from app.models.institucion import Institucion
from app.models.kiosk import Kiosko, PuntoAcceso
from app.models.operational import (
    AsignacionMedicoConsultorio,
    AsignacionOperador,
    ClusterTurnos,
    Consultorio,
    ConsultorioCluster,
    Medico,
    Operador,
    Piso,
    Role,
    SalaEspera,
    UsuarioRol,
)
from app.models.usuario import Usuario

ADMIN_EMAILS = ("admin1@example.com", "admin2@example.com")
ROLE_SEEDS = (
    ("ADMIN_SISTEMA", "Administrador de sistema", "Administración global de la plataforma."),
    ("ADMIN_NEGOCIO", "Administrador de negocio", "Administración por institución o complejo."),
    ("RECEPCIONISTA", "Recepcionista", "Lectura operativa y recepción por complejo."),
    ("MEDICO", "Médico", "Acceso de médico a sus datos operativos."),
    ("OPERADOR", "Operador", "Operación de flujos asignados."),
    ("GUARDIA_CONTINGENCIA", "Guardia de contingencia", "Operación limitada en contingencias."),
    ("USUARIO_KIOSKO", "Usuario kiosko", "Uso técnico para kioskos."),
)


def delete_all(db: Session, model: type) -> int:
    result = db.execute(delete(model))
    return int(result.rowcount or 0)


def ensure_roles(db: Session) -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for codigo, nombre, descripcion in ROLE_SEEDS:
        role = db.execute(select(Role).where(Role.codigo == codigo)).scalar_one_or_none()
        if role is None:
            role = Role(codigo=codigo, nombre=nombre, descripcion=descripcion)
            db.add(role)
            db.flush()
        role.activo = True
        roles[codigo] = role
    return roles


def ensure_admins(db: Session, password: str | None, admin_role: Role) -> list[Usuario]:
    admins: list[Usuario] = []
    for index, email in enumerate(ADMIN_EMAILS, start=1):
        admin = db.execute(select(Usuario).where(Usuario.email == email)).scalar_one_or_none()
        if admin is None:
            if not password:
                raise RuntimeError(
                    f"Falta {email}. Configura SEED_ADMIN_PASSWORD para poder recrear los dos administradores."
                )
            admin = Usuario(
                nombre=f"Administrador {index}",
                email=email,
                password_hash=hash_password(password),
                estado="ACTIVO",
            )
            db.add(admin)
            db.flush()
        else:
            admin.estado = "ACTIVO"
        db.add(UsuarioRol(usuario_id=admin.id, rol_id=admin_role.id))
        admins.append(admin)
    return admins


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)

    with SessionLocal() as db:
        missing_admins = [
            email
            for email in ADMIN_EMAILS
            if db.execute(select(Usuario.id).where(Usuario.email == email)).scalar_one_or_none() is None
        ]
        if missing_admins and not settings.seed_admin_password:
            missing = ", ".join(missing_admins)
            raise RuntimeError(
                f"No puedo limpiar todavía: faltan admins ({missing}) y SEED_ADMIN_PASSWORD no está configurada."
            )

        deleted = {
            "auditoria": delete_all(db, Auditoria),
            "usuario_roles": delete_all(db, UsuarioRol),
            "eventos_llegada": delete_all(db, EventoLlegada),
            "turnos_display": delete_all(db, TurnoDisplay),
            "qr_tokens": delete_all(db, QrToken),
            "citas": delete_all(db, Cita),
            "pacientes": delete_all(db, Paciente),
            "kioskos": delete_all(db, Kiosko),
            "pantallas_turnos_clusters": delete_all(db, PantallaTurnosCluster),
            "pantallas_turnos": delete_all(db, PantallaTurnos),
            "puntos_acceso": delete_all(db, PuntoAcceso),
            "consultorios_clusters": delete_all(db, ConsultorioCluster),
            "asignaciones_operador": delete_all(db, AsignacionOperador),
            "asignaciones_medico_consultorio": delete_all(db, AsignacionMedicoConsultorio),
            "operadores": delete_all(db, Operador),
            "medicos": delete_all(db, Medico),
            "consultorios": delete_all(db, Consultorio),
            "clusters_turnos": delete_all(db, ClusterTurnos),
            "salas_espera": delete_all(db, SalaEspera),
            "pisos": delete_all(db, Piso),
            "contactos_institucionales_complejos": delete_all(db, ContactoInstitucionalComplejo),
            "contactos_institucionales": delete_all(db, ContactoInstitucional),
            "complejos": delete_all(db, Complejo),
            "instituciones": delete_all(db, Institucion),
        }

        db.execute(delete(Usuario).where(Usuario.email.not_in(ADMIN_EMAILS)))
        roles = ensure_roles(db)
        admins = ensure_admins(db, settings.seed_admin_password, roles["ADMIN_SISTEMA"])

        db.add(
            Auditoria(
                evento="RESET_DATOS_PRUEBA",
                entidad="database",
                canal="CLI",
                valor_despues={
                    "usuarios_conservados": [admin.email for admin in admins],
                    "tablas_limpiadas": deleted,
                },
            )
        )
        db.commit()

    logger.info("reset_data_done", extra={"admins": ADMIN_EMAILS, "deleted": deleted})
    print("Base limpia. Usuarios conservados: " + ", ".join(ADMIN_EMAILS))
    print("Se conservan roles base y se reasignó ADMIN_SISTEMA global a ambos admins.")


if __name__ == "__main__":
    main()
