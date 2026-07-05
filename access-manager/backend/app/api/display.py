from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import (
    TURNO_TEMPLATE_DEFAULT,
    TURNO_TEMPLATE_PATIENT_CONSULTORIO,
    TURNO_TEMPLATE_PATIENT_TURNO_CONSULTORIO,
    TURNO_TEMPLATE_TURNO_CONSULTORIO,
    TURNO_TEMPLATE_TURNO_PATIENT_CONSULTORIO,
)
from app.core.database import get_db
from app.core.security import hash_password, require_role, verify_password
from app.models.complejo import Complejo
from app.models.display import PantallaTurnos, PantallaTurnosCluster, TurnoDisplay
from app.models.flow import Cita, Paciente
from app.models.operational import ClusterTurnos, Consultorio, ConsultorioCluster, Medico, Piso
from app.models.usuario import Usuario
from app.schemas.display import (
    CitaLlamarResponse,
    PantallaTurnosCreate,
    PantallaTurnosPublicConfig,
    PantallaTurnosRead,
    PantallaTurnosUpdate,
    PublicDisplayResponse,
    PublicTurnoDisplay,
    TurnoDisplayRecienteRead,
)
from app.services.audit_service import audit_safe_dict, record_audit_event

router = APIRouter()
AdminUser = Depends(require_role("ADMIN_SISTEMA", "ADMIN_NEGOCIO"))
OperationalUser = Depends(require_role("ADMIN_SISTEMA", "ADMIN_NEGOCIO", "RECEPCIONISTA", "MEDICO", "OPERADOR"))
CALL_INTERVAL = timedelta(minutes=5)
MAX_CALLS_PER_CITA = 3
TERMINAL_CALL_STATES = {"CANCELADA", "EXPIRADA", "FINALIZADA", "NO_LLEGO"}


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def now_utc() -> datetime:
    return datetime.now(UTC)


def exists_or_404(db: Session, model: type, item_id: UUID, label: str) -> object:
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} no encontrado.")
    return item


def cluster_ids_for_screen(db: Session, pantalla_id: UUID) -> list[UUID]:
    return list(
        db.execute(select(PantallaTurnosCluster.cluster_id).where(PantallaTurnosCluster.pantalla_id == pantalla_id)).scalars()
    )


def replace_screen_clusters(db: Session, pantalla_id: UUID, cluster_ids: list[UUID]) -> None:
    db.query(PantallaTurnosCluster).filter(PantallaTurnosCluster.pantalla_id == pantalla_id).delete()
    for cluster_id in cluster_ids:
        db.add(PantallaTurnosCluster(pantalla_id=pantalla_id, cluster_id=cluster_id))


def response_for_screen(db: Session, screen: PantallaTurnos) -> PantallaTurnosRead:
    return PantallaTurnosRead(
        id=screen.id,
        codigo_dispositivo=screen.codigo_dispositivo,
        complejo_id=screen.complejo_id,
        piso_id=screen.piso_id,
        cluster_espera_id=screen.cluster_espera_id,
        cluster_ids=cluster_ids_for_screen(db, screen.id),
        consultorio_id=screen.consultorio_id,
        nombre=screen.nombre,
        descripcion=screen.descripcion,
        activa=screen.activa,
        ultima_conexion=screen.ultima_conexion,
        polling_interval_seconds=screen.polling_interval_seconds,
        color_fondo=screen.color_fondo,
        color_texto=screen.color_texto,
        color_turno_nuevo=screen.color_turno_nuevo,
        color_turno_normal=screen.color_turno_normal,
        font_size_turno_nuevo=screen.font_size_turno_nuevo,
        font_size_turno_normal=screen.font_size_turno_normal,
        segundos_resaltado=screen.segundos_resaltado,
        segundos_visible=screen.segundos_visible,
        max_turnos_visibles=screen.max_turnos_visibles,
        created_at=screen.created_at,
        updated_at=screen.updated_at,
    )


def screen_audit(db: Session, screen: PantallaTurnos) -> dict:
    return {**audit_safe_dict(screen), "cluster_ids": [str(cluster_id) for cluster_id in cluster_ids_for_screen(db, screen.id)]}


def validate_clusters_for_screen(db: Session, cluster_ids: list[UUID], complejo_id: UUID | None, piso_id: UUID | None) -> None:
    if not cluster_ids:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Debe asignar al menos un clúster.")
    clusters = list(db.execute(select(ClusterTurnos).where(ClusterTurnos.id.in_(cluster_ids))).scalars())
    found = {cluster.id for cluster in clusters}
    missing = [str(cluster_id) for cluster_id in cluster_ids if cluster_id not in found]
    if missing:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Clústers no encontrados: {', '.join(missing)}")
    for cluster in clusters:
        if complejo_id is not None and cluster.complejo_id != complejo_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El clúster no pertenece al complejo indicado.")
        if piso_id is not None and cluster.piso_id != piso_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El clúster no pertenece al piso indicado.")


def cluster_ids_for_consultorio(db: Session, consultorio_id: UUID) -> list[UUID]:
    return list(
        db.execute(select(ConsultorioCluster.cluster_id).where(ConsultorioCluster.consultorio_id == consultorio_id)).scalars()
    )


def screen_ids_by_cluster(db: Session, cluster_ids: list[UUID]) -> dict[UUID, UUID]:
    rows = db.execute(
        select(PantallaTurnosCluster.cluster_id, PantallaTurnosCluster.pantalla_id)
        .join(PantallaTurnos, PantallaTurnos.id == PantallaTurnosCluster.pantalla_id)
        .where(PantallaTurnos.activa.is_(True), PantallaTurnosCluster.cluster_id.in_(cluster_ids))
        .order_by(PantallaTurnos.codigo_dispositivo)
    ).all()
    mapping: dict[UUID, UUID] = {}
    for cluster_id, pantalla_id in rows:
        mapping.setdefault(cluster_id, pantalla_id)
    return mapping


def consultorio_ids_for_clusters(db: Session, cluster_ids: list[UUID]) -> list[UUID]:
    if not cluster_ids:
        return []
    return list(
        db.execute(
            select(ConsultorioCluster.consultorio_id)
            .where(ConsultorioCluster.cluster_id.in_(cluster_ids))
            .distinct()
        ).scalars()
    )


def screen_change_keeps_consultorio_coverage(
    db: Session,
    screen: PantallaTurnos,
    new_cluster_ids: list[UUID] | None = None,
    active: bool | None = None,
) -> bool:
    current_cluster_ids = cluster_ids_for_screen(db, screen.id)
    affected_consultorio_ids = consultorio_ids_for_clusters(db, current_cluster_ids)
    target_active = screen.activa if active is None else active
    target_cluster_ids = current_cluster_ids if new_cluster_ids is None else new_cluster_ids
    for consultorio_id in affected_consultorio_ids:
        consultorio_cluster_ids = cluster_ids_for_consultorio(db, consultorio_id)
        has_other_screen = (
            db.execute(
                select(PantallaTurnosCluster)
                .join(PantallaTurnos, PantallaTurnos.id == PantallaTurnosCluster.pantalla_id)
                .where(
                    PantallaTurnos.activa.is_(True),
                    PantallaTurnos.id != screen.id,
                    PantallaTurnosCluster.cluster_id.in_(consultorio_cluster_ids),
                )
                .limit(1)
            ).first()
            is not None
        )
        has_this_screen = target_active and any(cluster_id in consultorio_cluster_ids for cluster_id in target_cluster_ids)
        if not has_other_screen and not has_this_screen:
            return False
    return True


def ensure_screen_change_keeps_consultorio_coverage(
    db: Session,
    screen: PantallaTurnos,
    new_cluster_ids: list[UUID] | None = None,
    active: bool | None = None,
) -> None:
    if not screen_change_keeps_consultorio_coverage(db, screen, new_cluster_ids, active):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se puede dejar un consultorio sin al menos un clúster con pantalla de turnos activa.",
        )


def validate_screen_scope(db: Session, data: dict, item: PantallaTurnos | None = None) -> None:
    complejo_id = data.get("complejo_id", getattr(item, "complejo_id", None))
    piso_id = data.get("piso_id", getattr(item, "piso_id", None))
    cluster_ids = data.get("cluster_ids")
    consultorio_id = data.get("consultorio_id", getattr(item, "consultorio_id", None))
    codigo_dispositivo = data.get("codigo_dispositivo")

    if complejo_id is not None:
        exists_or_404(db, Complejo, complejo_id, "Complejo")
    if piso_id is not None:
        piso = exists_or_404(db, Piso, piso_id, "Piso")
        if complejo_id is not None and piso.complejo_id != complejo_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El piso no pertenece al complejo indicado.")
    if consultorio_id is not None:
        consultorio = exists_or_404(db, Consultorio, consultorio_id, "Consultorio")
        if complejo_id is not None and consultorio.complejo_id != complejo_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El consultorio no pertenece al complejo indicado.")
        if piso_id is not None and consultorio.piso_id != piso_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El consultorio no pertenece al piso indicado.")
    if cluster_ids is not None:
        validate_clusters_for_screen(db, cluster_ids, complejo_id, piso_id)
        if item is not None:
            ensure_screen_change_keeps_consultorio_coverage(db, item, new_cluster_ids=cluster_ids)

    if codigo_dispositivo is not None:
        query = select(PantallaTurnos).where(PantallaTurnos.codigo_dispositivo == codigo_dispositivo)
        if item is not None:
            query = query.where(PantallaTurnos.id != item.id)
        if db.execute(query).scalar_one_or_none() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El código de dispositivo ya existe.")


def apply_screen_token(data: dict) -> dict:
    token_provided = "token" in data
    token = data.pop("token", None)
    if token_provided:
        data["token_hash"] = hash_password(token) if token else None
    return data


def display_config(screen: PantallaTurnos | None) -> PantallaTurnosPublicConfig:
    return PantallaTurnosPublicConfig(
        polling_interval_seconds=screen.polling_interval_seconds if screen else 5,
        color_fondo=screen.color_fondo if screen else None,
        color_texto=screen.color_texto if screen else None,
        color_turno_nuevo=screen.color_turno_nuevo if screen else None,
        color_turno_normal=screen.color_turno_normal if screen else None,
        font_size_turno_nuevo=screen.font_size_turno_nuevo if screen else None,
        font_size_turno_normal=screen.font_size_turno_normal if screen else None,
        segundos_resaltado=screen.segundos_resaltado if screen else 25,
        segundos_visible=screen.segundos_visible if screen else 300,
        max_turnos_visibles=screen.max_turnos_visibles if screen else 10,
    )


def sync_turno_states(db: Session, timestamp: datetime) -> None:
    turnos = db.execute(
        select(TurnoDisplay).where(TurnoDisplay.estado.in_(("NUEVO", "VISIBLE")))
    ).scalars()
    changed = False
    for turno in turnos:
        if turno.visible_hasta <= timestamp:
            turno.estado = "OCULTO"
            turno.ocultado_en = turno.ocultado_en or timestamp
            changed = True
        elif turno.estado == "NUEVO" and turno.resaltado_hasta <= timestamp:
            turno.estado = "VISIBLE"
            changed = True
    if changed:
        db.flush()


def consultorio_label(db: Session, consultorio_id: UUID) -> str:
    consultorio = exists_or_404(db, Consultorio, consultorio_id, "Consultorio")
    return consultorio.nombre_visible or consultorio.codigo


def consultorio_destination_text(label: str) -> str:
    text = label.strip()
    if text.lower().startswith("consultorio"):
        return f"consultorio{text[len('consultorio'):]}"
    return f"consultorio {text}"


def patient_turn_text(paciente: Paciente | None) -> str:
    if paciente is None:
        return "Paciente *"
    name = (paciente.nombre_preferido or paciente.nombre or "Paciente").strip()
    paternal_initial = (paciente.apellido_paterno or "").strip()[:1].upper()
    return f"{name} {paternal_initial}*".strip()


def render_turno_text(db: Session, cita: Cita, consultorio: str) -> str:
    medico = db.get(Medico, cita.medico_id)
    paciente = db.get(Paciente, cita.paciente_id)
    template = getattr(medico, "plantilla_turno", None) or TURNO_TEMPLATE_DEFAULT
    patient = patient_turn_text(paciente)
    destination = consultorio_destination_text(consultorio)

    if template == TURNO_TEMPLATE_TURNO_PATIENT_CONSULTORIO:
        return f"Turno {cita.folio_turno} del paciente {patient} a {destination}"
    if template == TURNO_TEMPLATE_PATIENT_TURNO_CONSULTORIO:
        return f"Paciente {patient} con turno {cita.folio_turno} a {destination}"
    if template == TURNO_TEMPLATE_TURNO_CONSULTORIO:
        return f"Turno {cita.folio_turno} a {destination}"
    if template == TURNO_TEMPLATE_PATIENT_CONSULTORIO:
        return f"Paciente {patient} a {destination}"
    return f"Paciente {patient} a {destination}"


def call_number_for_rows(rows: list[TurnoDisplay]) -> int:
    return max((row.llamado_numero or 1 for row in rows), default=0)


@router.get("/pantallas-turnos", response_model=list[PantallaTurnosRead])
def list_pantallas_turnos(
    db: Session = Depends(get_db),
    _current_user: Usuario = AdminUser,
) -> list[PantallaTurnosRead]:
    screens = list(db.execute(select(PantallaTurnos).order_by(PantallaTurnos.codigo_dispositivo)).scalars())
    return [response_for_screen(db, screen) for screen in screens]


@router.post("/pantallas-turnos", response_model=PantallaTurnosRead, status_code=status.HTTP_201_CREATED)
def create_pantalla_turnos(
    payload: PantallaTurnosCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = AdminUser,
) -> PantallaTurnosRead:
    data = apply_screen_token(payload.model_dump())
    cluster_ids = data.pop("cluster_ids")
    validate_screen_scope(db, data)
    validate_clusters_for_screen(db, cluster_ids, data["complejo_id"], data.get("piso_id"))
    item = PantallaTurnos(**data)
    db.add(item)
    db.flush()
    replace_screen_clusters(db, item.id, cluster_ids)
    db.flush()
    record_audit_event(
        db,
        evento="PANTALLA_TURNOS_CREADA",
        entidad="pantallas_turnos",
        entidad_id=item.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_despues=screen_audit(db, item),
    )
    db.commit()
    db.refresh(item)
    return response_for_screen(db, item)


@router.patch("/pantallas-turnos/{item_id}", response_model=PantallaTurnosRead)
def update_pantalla_turnos(
    item_id: UUID,
    payload: PantallaTurnosUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = AdminUser,
) -> PantallaTurnosRead:
    item = exists_or_404(db, PantallaTurnos, item_id, "Pantalla")
    before = screen_audit(db, item)
    data = payload.model_dump(exclude_unset=True)
    data = apply_screen_token(data)
    cluster_ids = data.pop("cluster_ids", None)
    validate_screen_scope(db, data, item)
    for key, value in data.items():
        setattr(item, key, value)
    db.flush()
    if cluster_ids is not None:
        validate_clusters_for_screen(db, cluster_ids, item.complejo_id, item.piso_id)
        ensure_screen_change_keeps_consultorio_coverage(db, item, new_cluster_ids=cluster_ids)
        replace_screen_clusters(db, item.id, cluster_ids)
        db.flush()
    record_audit_event(
        db,
        evento="PANTALLA_TURNOS_EDITADA",
        entidad="pantallas_turnos",
        entidad_id=item.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_antes=before,
        valor_despues=screen_audit(db, item),
    )
    db.commit()
    db.refresh(item)
    return response_for_screen(db, item)


@router.post("/pantallas-turnos/{item_id}/activar", response_model=PantallaTurnosRead)
def activar_pantalla_turnos(
    item_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = AdminUser,
) -> PantallaTurnosRead:
    return set_pantalla_active(item_id, True, request, db, current_user)


@router.post("/pantallas-turnos/{item_id}/desactivar", response_model=PantallaTurnosRead)
def desactivar_pantalla_turnos(
    item_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = AdminUser,
) -> PantallaTurnosRead:
    return set_pantalla_active(item_id, False, request, db, current_user)


def set_pantalla_active(
    item_id: UUID,
    active: bool,
    request: Request,
    db: Session,
    current_user: Usuario,
) -> PantallaTurnosRead:
    item = exists_or_404(db, PantallaTurnos, item_id, "Pantalla")
    before = screen_audit(db, item)
    if not active:
        ensure_screen_change_keeps_consultorio_coverage(db, item, active=False)
    item.activa = active
    db.flush()
    record_audit_event(
        db,
        evento="PANTALLA_TURNOS_EDITADA",
        entidad="pantallas_turnos",
        entidad_id=item.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_antes=before,
        valor_despues=screen_audit(db, item),
    )
    db.commit()
    db.refresh(item)
    return response_for_screen(db, item)


@router.get("/public-display/{codigo_dispositivo}/turnos", response_model=PublicDisplayResponse)
def public_display_turnos(
    codigo_dispositivo: str,
    token: str | None = Query(default=None),
    x_display_token: str | None = Header(default=None, alias="X-Display-Token"),
    db: Session = Depends(get_db),
) -> PublicDisplayResponse:
    timestamp = now_utc()
    screen = db.execute(
        select(PantallaTurnos).where(PantallaTurnos.codigo_dispositivo == codigo_dispositivo, PantallaTurnos.activa.is_(True))
    ).scalar_one_or_none()
    if screen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pantalla no encontrada.")
    if screen.token_hash:
        provided_token = token or x_display_token
        if not provided_token or not verify_password(provided_token, screen.token_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No fue posible autenticar el dispositivo.")

    sync_turno_states(db, timestamp)
    screen.ultima_conexion = timestamp

    screen_cluster_ids = cluster_ids_for_screen(db, screen.id)
    if not screen_cluster_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pantalla sin clústers asignados.")

    query = select(TurnoDisplay).where(
        TurnoDisplay.complejo_id == screen.complejo_id,
        TurnoDisplay.estado.notin_(("OCULTO", "CANCELADO")),
        TurnoDisplay.visible_hasta > timestamp,
        TurnoDisplay.ocultado_en.is_(None),
        TurnoDisplay.cluster_espera_id.in_(screen_cluster_ids),
    )

    config = display_config(screen)
    turnos = list(db.execute(query.order_by(TurnoDisplay.llamado_en.desc()).limit(config.max_turnos_visibles)).scalars())
    db.commit()
    return PublicDisplayResponse(
        codigo_dispositivo=screen.codigo_dispositivo,
        ultima_conexion=timestamp,
        config=config,
        turnos=[
            PublicTurnoDisplay(
                turno=item.turno,
                consultorio=item.consultorio,
                texto=item.texto_visible,
                estado=item.estado,
                llamado_en=item.llamado_en,
                resaltado=item.resaltado_hasta > timestamp and item.estado == "NUEVO",
            )
            for item in turnos
        ],
    )


@router.get("/turnos-display/recientes", response_model=list[TurnoDisplayRecienteRead])
def turnos_display_recientes(
    complejo_id: UUID,
    piso_id: UUID | None = None,
    cluster_espera_id: UUID | None = None,
    consultorio_id: UUID | None = None,
    minutos: int = Query(default=30, ge=1, le=240),
    db: Session = Depends(get_db),
    _current_user: Usuario = OperationalUser,
) -> list[TurnoDisplayRecienteRead]:
    timestamp = now_utc()
    sync_turno_states(db, timestamp)
    query = select(TurnoDisplay).where(
        TurnoDisplay.complejo_id == complejo_id,
        TurnoDisplay.llamado_en >= timestamp - timedelta(minutes=minutos),
    )
    if piso_id is not None:
        query = query.where(TurnoDisplay.piso_id == piso_id)
    if cluster_espera_id is not None:
        query = query.where(TurnoDisplay.cluster_espera_id == cluster_espera_id)
    if consultorio_id is not None:
        query = query.where(TurnoDisplay.consultorio_id == consultorio_id)
    rows = list(db.execute(query.order_by(TurnoDisplay.llamado_en.desc())).scalars())
    db.commit()
    recientes: list[TurnoDisplayRecienteRead] = []
    seen: set[tuple[UUID | None, int, datetime]] = set()
    for row in rows:
        call_number = row.llamado_numero or 1
        key = (row.cita_id, call_number, row.llamado_en)
        if key in seen:
            continue
        seen.add(key)
        cita = db.get(Cita, row.cita_id) if row.cita_id else None
        recientes.append(
            TurnoDisplayRecienteRead(
                cita_id=row.cita_id,
                turno=row.turno,
                consultorio=row.consultorio,
                texto=row.texto_visible,
                llamado_en=row.llamado_en,
                estado=row.estado,
                estado_cita=cita.estado if cita else None,
                llamado_numero=call_number,
            )
        )
    return recientes


@router.post("/citas/{cita_id}/llamar", response_model=CitaLlamarResponse, status_code=status.HTTP_201_CREATED)
def llamar_cita(
    cita_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = OperationalUser,
) -> CitaLlamarResponse:
    cita = exists_or_404(db, Cita, cita_id, "Cita")
    timestamp = now_utc()
    if cita.estado in TERMINAL_CALL_STATES:
        detail = "La cita está marcada como No Se Presentó." if cita.estado == "NO_LLEGO" else f"No se puede llamar una cita en estado {cita.estado}."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    call_rows = list(
        db.execute(
            select(TurnoDisplay)
            .where(TurnoDisplay.cita_id == cita.id)
            .order_by(TurnoDisplay.llamado_en.desc())
        ).scalars()
    )
    call_count = call_number_for_rows(call_rows)
    if call_count >= MAX_CALLS_PER_CITA:
        before = audit_safe_dict(cita)
        cita.estado = "NO_LLEGO"
        db.flush()
        record_audit_event(
            db,
            evento="CITA_NO_SE_PRESENTO",
            entidad="citas",
            entidad_id=cita.id,
            usuario_id=current_user.id,
            canal="WEB",
            ip_origen=client_ip(request),
            valor_antes=before,
            valor_despues=audit_safe_dict(cita),
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El paciente superó 3 llamados. Se marcó como No Se Presentó.",
        )

    last_call = call_rows[0] if call_rows else None
    if last_call is not None and last_call.llamado_en + CALL_INTERVAL > timestamp:
        remaining = (last_call.llamado_en + CALL_INTERVAL) - timestamp
        minutes = max(1, int((remaining.total_seconds() + 59) // 60))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Debe esperar {minutes} minuto(s) antes de volver a llamar este turno.",
        )

    consultorio_cluster_ids = cluster_ids_for_consultorio(db, cita.consultorio_id)
    screen_by_cluster = screen_ids_by_cluster(db, consultorio_cluster_ids)
    if not screen_by_cluster:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El consultorio debe estar asociado a por lo menos un clúster con una pantalla de turnos activa.",
        )
    screen = db.get(PantallaTurnos, next(iter(screen_by_cluster.values())))
    config = display_config(screen)
    consultorio_text = consultorio_label(db, cita.consultorio_id)
    texto_visible = render_turno_text(db, cita, consultorio_text)
    llamado_numero = call_count + 1
    first_item: TurnoDisplay | None = None
    for cluster_id, pantalla_id in screen_by_cluster.items():
        item = TurnoDisplay(
            cita_id=cita.id,
            pantalla_id=pantalla_id,
            complejo_id=cita.complejo_id,
            piso_id=cita.piso_id,
            cluster_espera_id=cluster_id,
            consultorio_id=cita.consultorio_id,
            turno=cita.folio_turno,
            consultorio=consultorio_text,
            texto_visible=texto_visible,
            llamado_numero=llamado_numero,
            estado="NUEVO",
            llamado_en=timestamp,
            resaltado_hasta=timestamp + timedelta(seconds=config.segundos_resaltado),
            visible_hasta=timestamp + timedelta(seconds=config.segundos_visible),
            llamado_por=current_user.id,
        )
        db.add(item)
        first_item = first_item or item
    db.flush()
    item = first_item
    event = "TURNO_RELLAMADO" if call_count else "TURNO_LLAMADO"
    record_audit_event(
        db,
        evento=event,
        entidad="turnos_display",
        entidad_id=item.id if item else cita.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_despues={
            "cita_id": str(cita.id),
            "cluster_ids": [str(cluster_id) for cluster_id in screen_by_cluster],
            "turno": cita.folio_turno,
            "texto": texto_visible,
            "llamado_numero": llamado_numero,
        },
    )
    if llamado_numero >= MAX_CALLS_PER_CITA:
        before = audit_safe_dict(cita)
        cita.estado = "NO_LLEGO"
        db.flush()
        record_audit_event(
            db,
            evento="CITA_NO_SE_PRESENTO",
            entidad="citas",
            entidad_id=cita.id,
            usuario_id=current_user.id,
            canal="WEB",
            ip_origen=client_ip(request),
            valor_antes=before,
            valor_despues=audit_safe_dict(cita),
        )
    db.commit()
    db.refresh(item)
    return CitaLlamarResponse(
        id=item.id,
        turno=item.turno,
        consultorio=item.consultorio,
        texto=item.texto_visible,
        estado=item.estado,
        estado_cita=cita.estado,
        llamado_numero=item.llamado_numero,
        llamado_en=item.llamado_en,
        resaltado_hasta=item.resaltado_hasta,
        visible_hasta=item.visible_hasta,
    )
