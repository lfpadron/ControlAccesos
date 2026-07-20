from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.core.security import hash_password
from app.models.complejo import Complejo
from app.models.display import PantallaTurnos, PantallaTurnosCluster
from app.models.flow import Cita, Paciente, QrToken
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
from app.services.folio_service import generate_turn_folio
from app.services.qr_service import generate_qr

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


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)

    if not settings.seed_admin_password:
        raise RuntimeError("SEED_ADMIN_PASSWORD debe estar configurada para crear usuarios semilla.")

    with SessionLocal() as db:
        roles: dict[str, Role] = {}
        for codigo, nombre, descripcion in ROLE_SEEDS:
            role = db.execute(select(Role).where(Role.codigo == codigo)).scalar_one_or_none()
            if role is None:
                role = Role(codigo=codigo, nombre=nombre, descripcion=descripcion)
                db.add(role)
                db.flush()
                logger.info("seed_role_created", extra={"codigo": codigo})
            roles[codigo] = role

        for email in ADMIN_EMAILS:
            existing = db.execute(select(Usuario).where(Usuario.email == email)).scalar_one_or_none()
            if existing:
                logger.info("seed_admin_exists", extra={"email": email})
                admin = existing
            else:
                admin = Usuario(
                    nombre=f"Administrador {email.split('@')[0][-1]}",
                    email=email,
                    password_hash=hash_password(settings.seed_admin_password),
                    estado="ACTIVO",
                )
                db.add(admin)
                db.flush()
                logger.info("seed_admin_created", extra={"email": email})

            admin_role = roles["ADMIN_SISTEMA"]
            assignment = db.execute(
                select(UsuarioRol).where(
                    UsuarioRol.usuario_id == admin.id,
                    UsuarioRol.rol_id == admin_role.id,
                    UsuarioRol.institucion_id.is_(None),
                    UsuarioRol.complejo_id.is_(None),
                )
            ).scalar_one_or_none()
            if assignment is None:
                db.add(UsuarioRol(usuario_id=admin.id, rol_id=admin_role.id))
                logger.info("seed_admin_role_created", extra={"email": email})

        institucion = db.execute(select(Institucion).where(Institucion.nombre == "Institución Demo")).scalar_one_or_none()
        if institucion is None:
            institucion = Institucion(nombre="Institución Demo", razon_social="Institución Demo S.A.")
            db.add(institucion)
            db.flush()

        complejo = db.execute(
            select(Complejo).where(Complejo.institucion_id == institucion.id, Complejo.nombre == "Torre Demo")
        ).scalar_one_or_none()
        if complejo is None:
            complejo = Complejo(
                institucion_id=institucion.id,
                nombre="Torre Demo",
                descripcion="Complejo demo para desarrollo local.",
                zona_horaria="America/Mexico_City",
            )
            db.add(complejo)
            db.flush()

        piso = db.execute(select(Piso).where(Piso.complejo_id == complejo.id, Piso.numero == "1")).scalar_one_or_none()
        if piso is None:
            piso = Piso(complejo_id=complejo.id, numero="1", nombre_visible="Piso 1")
            db.add(piso)
            db.flush()

        punto_acceso = db.execute(
            select(PuntoAcceso).where(PuntoAcceso.piso_id == piso.id, PuntoAcceso.nombre == "Lobby principal")
        ).scalar_one_or_none()
        if punto_acceso is None:
            punto_acceso = PuntoAcceso(
                complejo_id=complejo.id,
                piso_id=piso.id,
                nombre="Lobby principal",
                descripcion="Punto de acceso demo para kioskos.",
            )
            db.add(punto_acceso)
            db.flush()

        sala = db.execute(select(SalaEspera).where(SalaEspera.piso_id == piso.id, SalaEspera.nombre == "Sala Principal")).scalar_one_or_none()
        if sala is None:
            sala = SalaEspera(
                complejo_id=complejo.id,
                piso_id=piso.id,
                nombre="Sala Principal",
                capacidad_estimada=20,
            )
            db.add(sala)
            db.flush()

        cluster = db.execute(
            select(ClusterTurnos).where(ClusterTurnos.piso_id == piso.id, ClusterTurnos.nombre == "Clúster principal")
        ).scalar_one_or_none()
        if cluster is None:
            cluster = ClusterTurnos(
                complejo_id=complejo.id,
                piso_id=piso.id,
                nombre="Clúster principal",
                descripcion="Clúster demo para pantallas de turnos.",
            )
            db.add(cluster)
            db.flush()

        consultorio = db.execute(
            select(Consultorio).where(Consultorio.complejo_id == complejo.id, Consultorio.codigo == "C-101")
        ).scalar_one_or_none()
        if consultorio is None:
            consultorio = Consultorio(
                complejo_id=complejo.id,
                piso_id=piso.id,
                codigo="C-101",
                nombre_visible="Consultorio 101",
            )
            db.add(consultorio)
            db.flush()

        consultorio_cluster = db.execute(
            select(ConsultorioCluster).where(
                ConsultorioCluster.consultorio_id == consultorio.id,
                ConsultorioCluster.cluster_id == cluster.id,
            )
        ).scalar_one_or_none()
        if consultorio_cluster is None:
            db.add(ConsultorioCluster(consultorio_id=consultorio.id, cluster_id=cluster.id))
            db.flush()

        pantalla = db.execute(
            select(PantallaTurnos).where(PantallaTurnos.codigo_dispositivo == "demo-lobby")
        ).scalar_one_or_none()
        if pantalla is None:
            pantalla = PantallaTurnos(
                codigo_dispositivo="demo-lobby",
                nombre="Pantalla demo lobby",
                complejo_id=complejo.id,
                piso_id=piso.id,
                polling_interval_seconds=5,
                color_fondo="#06111f",
                color_texto="#f8fbff",
                color_turno_nuevo="#34d399",
                color_turno_normal="#f8fbff",
                font_size_turno_nuevo=96,
                font_size_turno_normal=64,
                segundos_resaltado=25,
                segundos_visible=300,
                max_turnos_visibles=10,
            )
            db.add(pantalla)
            db.flush()
        pantalla_cluster = db.execute(
            select(PantallaTurnosCluster).where(
                PantallaTurnosCluster.pantalla_id == pantalla.id,
                PantallaTurnosCluster.cluster_id == cluster.id,
            )
        ).scalar_one_or_none()
        if pantalla_cluster is None:
            db.add(PantallaTurnosCluster(pantalla_id=pantalla.id, cluster_id=cluster.id))
            db.flush()

        kiosko = db.execute(select(Kiosko).where(Kiosko.codigo_dispositivo == "demo-kiosko-lobby")).scalar_one_or_none()
        if kiosko is None:
            kiosko = Kiosko(
                codigo_dispositivo="demo-kiosko-lobby",
                token_hash=hash_password("kiosko-demo-token"),
                complejo_id=complejo.id,
                piso_id=piso.id,
                punto_acceso_id=punto_acceso.id,
                nombre="Kiosko demo lobby",
                polling_interval_seconds=5,
                color_fondo="white",
                color_texto="black",
                color_primario="royalblue",
                color_acento="seagreen",
            )
            db.add(kiosko)
            db.flush()

        medico = db.execute(
            select(Medico).where(Medico.nombre == "Médico", Medico.apellidos == "Demo")
        ).scalar_one_or_none()
        if medico is None:
            medico = Medico(nombre="Médico", apellidos="Demo", nombre_visible="Dr. Demo")
            db.add(medico)
            db.flush()

        operador_user = db.execute(select(Usuario).where(Usuario.email == "operador-demo@example.com")).scalar_one_or_none()
        if operador_user is None:
            operador_user = Usuario(
                nombre="Operador Demo",
                email="operador-demo@example.com",
                password_hash=hash_password(settings.seed_admin_password),
                estado="ACTIVO",
            )
            db.add(operador_user)
            db.flush()

        operador_role = roles["OPERADOR"]
        operador_role_assignment = db.execute(
            select(UsuarioRol).where(
                UsuarioRol.usuario_id == operador_user.id,
                UsuarioRol.rol_id == operador_role.id,
                UsuarioRol.institucion_id == institucion.id,
                UsuarioRol.complejo_id == complejo.id,
            )
        ).scalar_one_or_none()
        if operador_role_assignment is None:
            db.add(
                UsuarioRol(
                    usuario_id=operador_user.id,
                    rol_id=operador_role.id,
                    institucion_id=institucion.id,
                    complejo_id=complejo.id,
                )
            )

        operador = db.execute(select(Operador).where(Operador.usuario_id == operador_user.id)).scalar_one_or_none()
        if operador is None:
            operador = Operador(usuario_id=operador_user.id)
            db.add(operador)
            db.flush()

        asignacion_medico = db.execute(
            select(AsignacionMedicoConsultorio).where(
                AsignacionMedicoConsultorio.medico_id == medico.id,
                AsignacionMedicoConsultorio.consultorio_id == consultorio.id,
            )
        ).scalar_one_or_none()
        if asignacion_medico is None:
            asignacion_medico = AsignacionMedicoConsultorio(
                medico_id=medico.id,
                consultorio_id=consultorio.id,
                fecha_inicio=date(2026, 1, 1),
                dias_semana="L,M,X,J,V",
            )
            db.add(asignacion_medico)
            db.flush()

        asignacion_operador = db.execute(
            select(AsignacionOperador).where(
                AsignacionOperador.operador_id == operador.id,
                AsignacionOperador.consultorio_id == consultorio.id,
                AsignacionOperador.complejo_id == complejo.id,
            )
        ).scalar_one_or_none()
        if asignacion_operador is None:
            db.add(
                AsignacionOperador(
                    operador_id=operador.id,
                    consultorio_id=consultorio.id,
                    complejo_id=complejo.id,
                    fecha_inicio=date(2026, 1, 1),
                )
            )

        paciente = db.execute(select(Paciente).where(Paciente.folio_paciente == "PDEMO246")).scalar_one_or_none()
        if paciente is None:
            paciente = Paciente(
                folio_paciente="PDEMO246",
                nombre="Paciente",
                apellido_paterno="Demo",
                celular="5550100000",
                fecha_nacimiento=date(1970, 1, 1),
            )
            db.add(paciente)
            db.flush()
        else:
            if paciente.celular is None:
                paciente.celular = "5550100000"
            if paciente.fecha_nacimiento is None:
                paciente.fecha_nacimiento = date(1970, 1, 1)

        local_timezone = ZoneInfo(complejo.zona_horaria)
        checkin_target = datetime.now(local_timezone) + timedelta(minutes=60)
        today = checkin_target.date()
        checkin_time = checkin_target.time().replace(second=0, microsecond=0)

        cita_programada = db.execute(
            select(Cita).where(
                Cita.paciente_id == paciente.id,
                Cita.complejo_id == complejo.id,
                Cita.fecha_cita == today,
                Cita.tipo == "PROGRAMADA",
                Cita.origen == "SEED_DEMO",
            )
        ).scalar_one_or_none()
        if cita_programada is None:
            cita_programada = Cita(
                tipo="PROGRAMADA",
                estado="AGENDADA",
                paciente_id=paciente.id,
                medico_id=medico.id,
                consultorio_id=consultorio.id,
                complejo_id=complejo.id,
                piso_id=piso.id,
                sala_prevista_id=sala.id,
                fecha_cita=today,
                hora_cita=checkin_time,
                duracion_estimada=30,
                folio_turno=generate_turn_folio(db, complejo.id, today),
                origen="SEED_DEMO",
            )
            db.add(cita_programada)
            db.flush()

        cita_espontanea = db.execute(
            select(Cita).where(
                Cita.paciente_id == paciente.id,
                Cita.complejo_id == complejo.id,
                Cita.fecha_cita == today,
                Cita.tipo == "ESPONTANEA",
                Cita.origen == "SEED_DEMO",
            )
        ).scalar_one_or_none()
        if cita_espontanea is None:
            espontanea_time = (datetime.now(local_timezone) + timedelta(minutes=30)).time().replace(second=0, microsecond=0)
            cita_espontanea = Cita(
                tipo="ESPONTANEA",
                estado="AGENDADA",
                paciente_id=paciente.id,
                medico_id=medico.id,
                consultorio_id=consultorio.id,
                complejo_id=complejo.id,
                piso_id=piso.id,
                sala_prevista_id=sala.id,
                fecha_cita=today,
                hora_cita=espontanea_time,
                duracion_estimada=20,
                folio_turno=generate_turn_folio(db, complejo.id, today),
                origen="SEED_DEMO",
            )
            db.add(cita_espontanea)
            db.flush()

        active_qr = db.execute(
            select(QrToken).where(QrToken.cita_id == cita_programada.id, QrToken.estado == "GENERADO")
        ).scalar_one_or_none()
        if active_qr is None:
            generate_qr(db, cita_programada)

        db.commit()


if __name__ == "__main__":
    main()
