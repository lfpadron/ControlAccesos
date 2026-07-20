from __future__ import annotations

from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.complejo import Complejo
from app.models.display import PantallaTurnos, PantallaTurnosCluster
from app.models.flow import Cita, EventoLlegada, Paciente, QrToken
from app.models.operational import Consultorio, ConsultorioCluster, Medico, Piso, SalaEspera
from app.models.usuario import Usuario
from app.schemas.flow import (
    CheckinRequest,
    CheckinResponse,
    CitaActionResponse,
    CitaCreate,
    CitaListItem,
    CitaRead,
    CitaSearchResult,
    CitaUpdate,
    PacienteCreate,
    PacienteRead,
    PacienteUpdate,
    QrCheckinRequest,
    QrGenerateResponse,
    QrRead,
    QrValidarRequest,
    QrValidarResponse,
    TicketResponse,
)
from app.services.audit_service import audit_safe_dict, record_audit_event
from app.services.checkin_service import checkin_window_status
from app.services.folio_service import generate_patient_folio, generate_turn_folio
from app.services.qr_service import cancel_qr, encode_qr_payload, generate_qr, now_utc, token_digest, validate_qr

pacientes_router = APIRouter()
citas_router = APIRouter()
qr_router = APIRouter()

OperationalUser = Depends(require_role("ADMIN_SISTEMA", "ADMIN_NEGOCIO", "RECEPCIONISTA", "MEDICO", "OPERADOR"))


def business_today() -> date:
    return datetime.now(ZoneInfo("America/Mexico_City")).date()


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def exists_or_404(db: Session, model: type, item_id: UUID, label: str) -> object:
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} no encontrado.")
    return item


def normalize_search(value: str) -> str:
    return f"%{value.strip().lower()}%"


def normalized_digits(value: str | None) -> str | None:
    if value is None:
        return None
    digits = "".join(char for char in value if char.isdigit())
    return digits or None


def patient_full_name(paciente: Paciente | None) -> str | None:
    if paciente is None:
        return None
    parts = [paciente.nombre, paciente.apellido_paterno, paciente.apellido_materno]
    text = " ".join(part for part in parts if part)
    return text or None


def patient_display_name(paciente: Paciente | None) -> str | None:
    if paciente is None:
        return None
    return paciente.nombre_preferido or patient_full_name(paciente)


def patient_medical_name(paciente: Paciente | None) -> str | None:
    if paciente is None:
        return None
    full_name = patient_full_name(paciente)
    if paciente.nombre_preferido and full_name:
        return f"{paciente.nombre_preferido} ({full_name})"
    return paciente.nombre_preferido or full_name


def consultorio_label(consultorio: Consultorio | None) -> str | None:
    if consultorio is None:
        return None
    return consultorio.nombre_visible or consultorio.codigo


def piso_label(piso: Piso | None) -> str | None:
    if piso is None:
        return None
    return piso.nombre_visible or f"Piso {piso.numero}"


def medico_label(medico: Medico | None) -> str | None:
    if medico is None:
        return None
    return medico.nombre_visible or f"{medico.nombre} {medico.apellidos}"


def cita_zona_horaria(db: Session, cita: Cita) -> str:
    complejo = db.get(Complejo, cita.complejo_id)
    return complejo.zona_horaria if complejo is not None else "UTC"


def cita_item(db: Session, cita: Cita) -> CitaListItem:
    payload = CitaRead.model_validate(cita).model_dump()
    paciente = db.get(Paciente, cita.paciente_id)
    return CitaListItem(
        **payload,
        paciente=patient_display_name(paciente),
        paciente_nombre_completo=patient_medical_name(paciente),
        consultorio=consultorio_label(db.get(Consultorio, cita.consultorio_id)),
        piso=piso_label(db.get(Piso, cita.piso_id)),
        medico=medico_label(db.get(Medico, cita.medico_id)),
    )


def cita_search_item(db: Session, cita: Cita) -> CitaSearchResult:
    return CitaSearchResult(
        id=cita.id,
        folio_turno=cita.folio_turno,
        hora_cita=cita.hora_cita,
        consultorio=consultorio_label(db.get(Consultorio, cita.consultorio_id)),
        piso=piso_label(db.get(Piso, cita.piso_id)),
        estado=cita.estado,
    )


def validate_patient_contact(paciente: Paciente) -> None:
    if not paciente.celular and paciente.fecha_nacimiento is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Debe indicar celular o fecha de nacimiento.",
        )


def validate_patient_identity(paciente: Paciente) -> None:
    if not paciente.nombre_preferido and not (paciente.nombre and paciente.apellido_paterno):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Debe indicar nombre preferido o nombre y apellido paterno.",
        )


def consultorio_has_display_coverage(db: Session, consultorio_id: UUID) -> bool:
    cluster_ids = list(
        db.execute(select(ConsultorioCluster.cluster_id).where(ConsultorioCluster.consultorio_id == consultorio_id)).scalars()
    )
    if not cluster_ids:
        return False
    return (
        db.execute(
            select(PantallaTurnosCluster)
            .join(PantallaTurnos, PantallaTurnos.id == PantallaTurnosCluster.pantalla_id)
            .where(PantallaTurnos.activa.is_(True), PantallaTurnosCluster.cluster_id.in_(cluster_ids))
            .limit(1)
        ).first()
        is not None
    )


def validate_cita_scope(db: Session, data: dict, item: Cita | None = None) -> None:
    paciente_id = data.get("paciente_id", getattr(item, "paciente_id", None))
    medico_id = data.get("medico_id", getattr(item, "medico_id", None))
    consultorio_id = data.get("consultorio_id", getattr(item, "consultorio_id", None))
    complejo_id = data.get("complejo_id", getattr(item, "complejo_id", None))
    piso_id = data.get("piso_id", getattr(item, "piso_id", None))
    sala_prevista_id = data.get("sala_prevista_id", getattr(item, "sala_prevista_id", None))

    if paciente_id is not None:
        exists_or_404(db, Paciente, paciente_id, "Paciente")
    if medico_id is not None:
        exists_or_404(db, Medico, medico_id, "Médico")
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
        if not consultorio_has_display_coverage(db, consultorio.id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El consultorio debe estar asociado a por lo menos un clúster con una pantalla de turnos activa.",
            )
    if sala_prevista_id is not None:
        sala = exists_or_404(db, SalaEspera, sala_prevista_id, "Sala de espera")
        if complejo_id is not None and sala.complejo_id != complejo_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La sala no pertenece al complejo indicado.")
        if piso_id is not None and sala.piso_id != piso_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La sala no pertenece al piso indicado.")


def duplicate_warnings(db: Session, data: dict, exclude_id: UUID | None = None) -> list[dict[str, str]]:
    paciente = db.get(Paciente, data["paciente_id"])
    if paciente is None:
        return []
    query = select(Cita).join(Paciente, Cita.paciente_id == Paciente.id).where(
        Cita.fecha_cita == data["fecha_cita"],
        Cita.medico_id == data["medico_id"],
        Cita.estado.notin_(("CANCELADA", "EXPIRADA")),
    )
    if paciente.nombre_preferido:
        query = query.where(func.lower(func.coalesce(Paciente.nombre_preferido, "")) == paciente.nombre_preferido.lower())
    elif paciente.nombre and paciente.apellido_paterno:
        query = query.where(
            func.lower(func.coalesce(Paciente.nombre, "")) == paciente.nombre.lower(),
            func.lower(func.coalesce(Paciente.apellido_paterno, "")) == paciente.apellido_paterno.lower(),
        )
    else:
        return []
    if not paciente.nombre_preferido and paciente.apellido_materno:
        query = query.where(func.lower(Paciente.apellido_materno) == paciente.apellido_materno.lower())
    if paciente.celular:
        query = query.where(Paciente.celular == paciente.celular)
    elif paciente.fecha_nacimiento:
        query = query.where(Paciente.fecha_nacimiento == paciente.fecha_nacimiento)
    else:
        return []
    if exclude_id is not None:
        query = query.where(Cita.id != exclude_id)
    return [
        {"cita_id": str(cita.id), "folio_turno": cita.folio_turno, "estado": cita.estado}
        for cita in db.execute(query.limit(5)).scalars()
    ]


def query_citas(
    db: Session,
    fecha: date | None = None,
    complejo_id: UUID | None = None,
    piso_id: UUID | None = None,
    consultorio_id: UUID | None = None,
    medico_id: UUID | None = None,
    paciente: str | None = None,
    celular: str | None = None,
    fecha_nacimiento: date | None = None,
    estado: str | None = None,
    tipo: str | None = None,
):
    query = select(Cita)
    patient_joined = False
    if paciente:
        patient_joined = True
        full_name = func.lower(
            func.coalesce(Paciente.nombre, "")
            + " "
            + func.coalesce(Paciente.apellido_paterno, "")
            + " "
            + func.coalesce(Paciente.apellido_materno, "")
            + " "
            + func.coalesce(Paciente.nombre_preferido, "")
        )
        query = query.join(Paciente, Cita.paciente_id == Paciente.id)
        for term_text in paciente.split():
            term = normalize_search(term_text)
            query = query.where(
                or_(
                    full_name.like(term),
                    func.lower(Paciente.celular).like(term),
                    func.lower(Paciente.folio_paciente).like(term),
                )
            )
    if celular:
        if not patient_joined:
            query = query.join(Paciente, Cita.paciente_id == Paciente.id)
            patient_joined = True
        digits = normalized_digits(celular)
        if digits:
            celular_digits = func.replace(
                func.replace(
                    func.replace(func.replace(func.replace(func.coalesce(Paciente.celular, ""), " ", ""), "-", ""), "(", ""),
                    ")",
                    "",
                ),
                "+",
                "",
            )
            query = query.where(celular_digits.like(f"%{digits}%"))
    if fecha_nacimiento is not None:
        if not patient_joined:
            query = query.join(Paciente, Cita.paciente_id == Paciente.id)
        query = query.where(Paciente.fecha_nacimiento == fecha_nacimiento)
    if fecha is not None:
        query = query.where(Cita.fecha_cita == fecha)
    if complejo_id is not None:
        query = query.where(Cita.complejo_id == complejo_id)
    if piso_id is not None:
        query = query.where(Cita.piso_id == piso_id)
    if consultorio_id is not None:
        query = query.where(Cita.consultorio_id == consultorio_id)
    if medico_id is not None:
        query = query.where(Cita.medico_id == medico_id)
    if estado is not None:
        query = query.where(Cita.estado == estado)
    if tipo is not None:
        query = query.where(Cita.tipo == tipo)
    return query.order_by(Cita.fecha_cita.desc(), Cita.hora_cita.desc())


def get_active_qr_payload(db: Session, cita: Cita) -> tuple[QrToken, str]:
    timestamp = now_utc()
    qr_token = db.execute(
        select(QrToken).where(
            QrToken.cita_id == cita.id,
            QrToken.estado == "GENERADO",
            QrToken.fecha_expiracion > timestamp,
        ).order_by(QrToken.fecha_emision.desc())
    ).scalar_one_or_none()
    if qr_token is not None:
        token = encode_qr_payload(cita, qr_token.fecha_emision, qr_token.fecha_expiracion)
        if token_digest(token) == qr_token.token_hash:
            return qr_token, token
    return generate_qr(db, cita)


def create_arrival_event(
    db: Session,
    cita: Cita,
    tipo: str,
    canal: str,
    request: Request,
    sala_id: UUID | None = None,
    usuario_id: UUID | None = None,
    dispositivo_id: str | None = None,
) -> EventoLlegada:
    timestamp = now_utc()
    event = EventoLlegada(
        cita_id=cita.id,
        tipo=tipo,
        sala_id=sala_id,
        canal=canal,
        usuario_id=usuario_id,
        dispositivo_id=dispositivo_id,
        ip_origen=client_ip(request),
        created_at=timestamp,
    )
    db.add(event)
    if tipo == "CHECKIN_LOBBY":
        cita.estado = "LLEGO_LOBBY"
    db.flush()
    return event


@pacientes_router.get("/buscar", response_model=list[PacienteRead])
def buscar_pacientes(
    q: str = Query(min_length=1),
    db: Session = Depends(get_db),
    _current_user: Usuario = OperationalUser,
) -> list[Paciente]:
    term = normalize_search(q)
    return list(
        db.execute(
            select(Paciente)
            .where(
                or_(
                    func.lower(func.coalesce(Paciente.nombre, "")).like(term),
                    func.lower(func.coalesce(Paciente.nombre_preferido, "")).like(term),
                    func.lower(func.coalesce(Paciente.apellido_paterno, "")).like(term),
                    func.lower(func.coalesce(Paciente.apellido_materno, "")).like(term),
                    func.lower(func.coalesce(Paciente.celular, "")).like(term),
                    func.lower(Paciente.folio_paciente).like(term),
                )
            )
            .order_by(func.coalesce(Paciente.nombre_preferido, Paciente.apellido_paterno, Paciente.nombre))
            .limit(50)
        ).scalars()
    )


@pacientes_router.get("", response_model=list[PacienteRead])
def list_pacientes(db: Session = Depends(get_db), _current_user: Usuario = OperationalUser) -> list[Paciente]:
    return list(
        db.execute(
            select(Paciente).order_by(func.coalesce(Paciente.nombre_preferido, Paciente.apellido_paterno, Paciente.nombre)).limit(200)
        ).scalars()
    )


@pacientes_router.get("/{paciente_id}", response_model=PacienteRead)
def get_paciente(paciente_id: UUID, db: Session = Depends(get_db), _current_user: Usuario = OperationalUser) -> Paciente:
    return exists_or_404(db, Paciente, paciente_id, "Paciente")


@pacientes_router.post("", response_model=PacienteRead, status_code=status.HTTP_201_CREATED)
def create_paciente(
    payload: PacienteCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = OperationalUser,
) -> Paciente:
    item = Paciente(**payload.model_dump(), folio_paciente=generate_patient_folio(db))
    db.add(item)
    db.flush()
    record_audit_event(
        db,
        evento="PACIENTE_CREADO",
        entidad="pacientes",
        entidad_id=item.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_despues=audit_safe_dict(item),
    )
    db.commit()
    db.refresh(item)
    return item


@pacientes_router.put("/{paciente_id}", response_model=PacienteRead)
def update_paciente(
    paciente_id: UUID,
    payload: PacienteUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = OperationalUser,
) -> Paciente:
    item = exists_or_404(db, Paciente, paciente_id, "Paciente")
    before = audit_safe_dict(item)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    validate_patient_identity(item)
    validate_patient_contact(item)
    db.flush()
    record_audit_event(
        db,
        evento="PACIENTE_EDITADO",
        entidad="pacientes",
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


@pacientes_router.patch("/{paciente_id}/activar", response_model=PacienteRead)
def activar_paciente(paciente_id: UUID, request: Request, db: Session = Depends(get_db), current_user: Usuario = OperationalUser) -> Paciente:
    return set_paciente_active(paciente_id, True, request, db, current_user)


@pacientes_router.patch("/{paciente_id}/desactivar", response_model=PacienteRead)
def desactivar_paciente(paciente_id: UUID, request: Request, db: Session = Depends(get_db), current_user: Usuario = OperationalUser) -> Paciente:
    return set_paciente_active(paciente_id, False, request, db, current_user)


def set_paciente_active(paciente_id: UUID, active: bool, request: Request, db: Session, current_user: Usuario) -> Paciente:
    item = exists_or_404(db, Paciente, paciente_id, "Paciente")
    before = audit_safe_dict(item)
    item.activo = active
    item.desactivado_en = None if active else now_utc()
    db.flush()
    record_audit_event(
        db,
        evento="PACIENTE_EDITADO",
        entidad="pacientes",
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


@pacientes_router.patch("/{paciente_id}/marcar-borrado", response_model=PacienteRead)
def marcar_paciente_borrado(
    paciente_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = OperationalUser,
) -> Paciente:
    item = exists_or_404(db, Paciente, paciente_id, "Paciente")
    before = audit_safe_dict(item)
    item.marcado_borrado_en = now_utc()
    db.flush()
    record_audit_event(
        db,
        evento="PACIENTE_MARCADO_BORRADO",
        entidad="pacientes",
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


@citas_router.get("/hoy", response_model=list[CitaListItem])
def citas_hoy(
    fecha: date | None = None,
    complejo_id: UUID | None = None,
    piso_id: UUID | None = None,
    consultorio_id: UUID | None = None,
    medico_id: UUID | None = None,
    paciente: str | None = None,
    estado: str | None = None,
    tipo: str | None = None,
    db: Session = Depends(get_db),
    _current_user: Usuario = OperationalUser,
) -> list[CitaListItem]:
    rows = db.execute(
        query_citas(db, fecha or business_today(), complejo_id, piso_id, consultorio_id, medico_id, paciente, None, None, estado, tipo)
    ).scalars()
    return [cita_item(db, row) for row in rows]


@citas_router.get("/buscar", response_model=list[CitaSearchResult])
def buscar_citas(
    paciente: str = Query(min_length=1),
    fecha: date | None = None,
    complejo_id: UUID | None = None,
    piso_id: UUID | None = None,
    consultorio_id: UUID | None = None,
    medico_id: UUID | None = None,
    celular: str | None = None,
    fecha_nacimiento: date | None = None,
    estado: str | None = None,
    tipo: str | None = None,
    db: Session = Depends(get_db),
) -> list[CitaSearchResult]:
    rows = db.execute(
        query_citas(
            db,
            fecha or business_today(),
            complejo_id,
            piso_id,
            consultorio_id,
            medico_id,
            paciente,
            celular,
            fecha_nacimiento,
            estado,
            tipo,
        ).limit(20)
    ).scalars()
    return [cita_search_item(db, row) for row in rows]


@citas_router.get("", response_model=list[CitaListItem])
def list_citas(
    fecha: date | None = None,
    complejo_id: UUID | None = None,
    piso_id: UUID | None = None,
    consultorio_id: UUID | None = None,
    medico_id: UUID | None = None,
    paciente: str | None = None,
    estado: str | None = None,
    tipo: str | None = None,
    db: Session = Depends(get_db),
    _current_user: Usuario = OperationalUser,
) -> list[CitaListItem]:
    rows = db.execute(query_citas(db, fecha, complejo_id, piso_id, consultorio_id, medico_id, paciente, None, None, estado, tipo).limit(200)).scalars()
    return [cita_item(db, row) for row in rows]


@citas_router.post("/exportacion", status_code=status.HTTP_201_CREATED)
def registrar_exportacion_citas(
    request: Request,
    formato: str = Query(pattern="^(excel|csv|json)$"),
    fecha: date | None = None,
    complejo_id: UUID | None = None,
    piso_id: UUID | None = None,
    consultorio_id: UUID | None = None,
    medico_id: UUID | None = None,
    paciente: str | None = None,
    estado: str | None = None,
    tipo: str | None = None,
    db: Session = Depends(get_db),
    current_user: Usuario = OperationalUser,
) -> dict[str, bool]:
    record_audit_event(
        db,
        evento="CITAS_EXPORTADAS",
        entidad="citas",
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_despues={
            "formato": formato,
            "fecha": str(fecha or business_today()),
            "complejo_id": str(complejo_id) if complejo_id else None,
            "piso_id": str(piso_id) if piso_id else None,
            "consultorio_id": str(consultorio_id) if consultorio_id else None,
            "medico_id": str(medico_id) if medico_id else None,
            "paciente": paciente,
            "estado": estado,
            "tipo": tipo,
        },
    )
    db.commit()
    return {"ok": True}


@citas_router.get("/{cita_id}", response_model=CitaListItem)
def get_cita(cita_id: UUID, db: Session = Depends(get_db), _current_user: Usuario = OperationalUser) -> CitaListItem:
    return cita_item(db, exists_or_404(db, Cita, cita_id, "Cita"))


@citas_router.post("", response_model=CitaRead, status_code=status.HTTP_201_CREATED)
def create_cita(
    payload: CitaCreate,
    request: Request,
    confirmar_duplicado: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: Usuario = OperationalUser,
) -> Cita:
    data = payload.model_dump()
    validate_cita_scope(db, data)
    warnings = duplicate_warnings(db, data)
    if warnings and not confirmar_duplicado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"mensaje": "Existe una posible cita duplicada. Confirme para crearla.", "duplicados": warnings},
        )
    item = Cita(**data, folio_turno=generate_turn_folio(db, payload.complejo_id, payload.fecha_cita), creada_por=current_user.id)
    db.add(item)
    db.flush()
    record_audit_event(
        db,
        evento="CITA_CREADA",
        entidad="citas",
        entidad_id=item.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_despues=audit_safe_dict(item),
    )
    db.commit()
    db.refresh(item)
    return item


@citas_router.put("/{cita_id}", response_model=CitaRead)
def update_cita(
    cita_id: UUID,
    payload: CitaUpdate,
    request: Request,
    confirmar_duplicado: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: Usuario = OperationalUser,
) -> Cita:
    item = exists_or_404(db, Cita, cita_id, "Cita")
    before = audit_safe_dict(item)
    data = payload.model_dump(exclude_unset=True)
    merged = {
        "paciente_id": data.get("paciente_id", item.paciente_id),
        "medico_id": data.get("medico_id", item.medico_id),
        "consultorio_id": data.get("consultorio_id", item.consultorio_id),
        "complejo_id": data.get("complejo_id", item.complejo_id),
        "piso_id": data.get("piso_id", item.piso_id),
        "sala_prevista_id": data.get("sala_prevista_id", item.sala_prevista_id),
        "fecha_cita": data.get("fecha_cita", item.fecha_cita),
        "hora_cita": data.get("hora_cita", item.hora_cita),
    }
    validate_cita_scope(db, merged, item)
    warnings = duplicate_warnings(db, merged, exclude_id=item.id)
    if warnings and not confirmar_duplicado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"mensaje": "Existe una posible cita duplicada. Confirme para actualizarla.", "duplicados": warnings},
        )
    regenerate_folio = "complejo_id" in data or "fecha_cita" in data
    for key, value in data.items():
        setattr(item, key, value)
    if regenerate_folio:
        item.folio_turno = generate_turn_folio(db, item.complejo_id, item.fecha_cita)
    db.flush()
    record_audit_event(
        db,
        evento="CITA_EDITADA",
        entidad="citas",
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


def set_cita_state(cita_id: UUID, state: str, event_name: str, request: Request, db: Session, current_user: Usuario) -> CitaActionResponse:
    item = exists_or_404(db, Cita, cita_id, "Cita")
    before = audit_safe_dict(item)
    item.estado = state
    db.flush()
    record_audit_event(
        db,
        evento=event_name,
        entidad="citas",
        entidad_id=item.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_antes=before,
        valor_despues=audit_safe_dict(item),
    )
    db.commit()
    db.refresh(item)
    return CitaActionResponse(id=item.id, estado=item.estado, folio_turno=item.folio_turno)


@citas_router.patch("/{cita_id}/cancelar", response_model=CitaActionResponse)
def cancelar_cita(cita_id: UUID, request: Request, db: Session = Depends(get_db), current_user: Usuario = OperationalUser):
    cancel_qr(db, cita_id)
    return set_cita_state(cita_id, "CANCELADA", "CITA_CANCELADA", request, db, current_user)


@citas_router.patch("/{cita_id}/autorizar-pasar", response_model=CitaActionResponse)
def autorizar_pasar(cita_id: UUID, request: Request, db: Session = Depends(get_db), current_user: Usuario = OperationalUser):
    return set_cita_state(cita_id, "AUTORIZADO_PASAR", "ACCESO_AUTORIZADO", request, db, current_user)


@citas_router.patch("/{cita_id}/iniciar-consulta", response_model=CitaActionResponse)
def iniciar_consulta(cita_id: UUID, request: Request, db: Session = Depends(get_db), current_user: Usuario = OperationalUser):
    return set_cita_state(cita_id, "EN_CONSULTA", "CONSULTA_INICIADA", request, db, current_user)


@citas_router.patch("/{cita_id}/finalizar", response_model=CitaActionResponse)
def finalizar_consulta(cita_id: UUID, request: Request, db: Session = Depends(get_db), current_user: Usuario = OperationalUser):
    return set_cita_state(cita_id, "FINALIZADA", "CONSULTA_FINALIZADA", request, db, current_user)


@citas_router.post("/{cita_id}/qr", response_model=QrGenerateResponse, status_code=status.HTTP_201_CREATED)
def generar_qr_cita(cita_id: UUID, request: Request, db: Session = Depends(get_db), current_user: Usuario = OperationalUser):
    cita = exists_or_404(db, Cita, cita_id, "Cita")
    qr_token, token = generate_qr(db, cita)
    record_audit_event(
        db,
        evento="QR_GENERADO",
        entidad="qr_tokens",
        entidad_id=qr_token.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
        valor_despues={"cita_id": str(cita.id), "estado": qr_token.estado, "fecha_expiracion": qr_token.fecha_expiracion.isoformat()},
    )
    db.commit()
    db.refresh(qr_token)
    return QrGenerateResponse(
        id=qr_token.id,
        cita_id=qr_token.cita_id,
        estado=qr_token.estado,
        fecha_emision=qr_token.fecha_emision,
        fecha_expiracion=qr_token.fecha_expiracion,
        qr_payload=token,
    )


@citas_router.get("/{cita_id}/qr", response_model=QrRead)
def get_qr_cita(cita_id: UUID, db: Session = Depends(get_db), _current_user: Usuario = OperationalUser):
    cita = exists_or_404(db, Cita, cita_id, "Cita")
    qr_token, _token = get_active_qr_payload(db, cita)
    db.commit()
    db.refresh(qr_token)
    return qr_token


@citas_router.patch("/{cita_id}/qr/cancelar", response_model=CitaActionResponse)
def cancelar_qr_cita(cita_id: UUID, request: Request, db: Session = Depends(get_db), current_user: Usuario = OperationalUser):
    cita = exists_or_404(db, Cita, cita_id, "Cita")
    cancel_qr(db, cita.id)
    record_audit_event(
        db,
        evento="QR_CANCELADO",
        entidad="citas",
        entidad_id=cita.id,
        usuario_id=current_user.id,
        canal="WEB",
        ip_origen=client_ip(request),
    )
    db.commit()
    return CitaActionResponse(id=cita.id, estado=cita.estado, folio_turno=cita.folio_turno)


@citas_router.get("/{cita_id}/ticket", response_model=TicketResponse)
def get_ticket_cita(cita_id: UUID, db: Session = Depends(get_db), _current_user: Usuario = OperationalUser):
    cita = exists_or_404(db, Cita, cita_id, "Cita")
    _qr_token, token = get_active_qr_payload(db, cita)
    db.commit()
    dias = ("LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO")
    consultorio = db.get(Consultorio, cita.consultorio_id)
    piso = db.get(Piso, cita.piso_id)
    return TicketResponse(
        encabezado_fecha=f"{dias[cita.fecha_cita.weekday()]}-{cita.fecha_cita.day:02d}",
        leyenda="VÁLIDO SOLO HOY",
        turno=cita.folio_turno,
        qr_payload=token,
        consultorio=consultorio_label(consultorio) or "",
        piso=piso_label(piso) or "",
        hora=cita.hora_cita.strftime("%H:%M"),
    )


@citas_router.post("/{cita_id}/checkin-lobby", response_model=CheckinResponse)
def checkin_lobby_cita(cita_id: UUID, payload: CheckinRequest, request: Request, db: Session = Depends(get_db)):
    cita = exists_or_404(db, Cita, cita_id, "Cita")
    if cita.estado in {"CANCELADA", "EXPIRADA", "NO_LLEGO"}:
        return CheckinResponse(resultado="ROJO", mensaje=f"La cita está en estado {cita.estado}.", cita_id=cita.id, folio_turno=cita.folio_turno, estado_cita=cita.estado)
    resultado, mensaje = checkin_window_status(cita, zona_horaria=cita_zona_horaria(db, cita))
    if resultado != "ROJO":
        event = create_arrival_event(db, cita, "CHECKIN_LOBBY", payload.canal, request, payload.sala_id, dispositivo_id=payload.dispositivo_id)
        record_audit_event(
            db,
            evento="CHECKIN_LOBBY",
            entidad="eventos_llegada",
            entidad_id=event.id,
            canal=payload.canal,
            ip_origen=client_ip(request),
            valor_despues={"cita_id": str(cita.id), "resultado": resultado},
        )
        db.commit()
        db.refresh(cita)
    return CheckinResponse(resultado=resultado, mensaje=mensaje, cita_id=cita.id, folio_turno=cita.folio_turno, estado_cita=cita.estado)


@citas_router.post("/{cita_id}/checkin-sala", response_model=CheckinResponse)
def checkin_sala_cita(cita_id: UUID, payload: CheckinRequest, request: Request, db: Session = Depends(get_db), current_user: Usuario = OperationalUser):
    cita = exists_or_404(db, Cita, cita_id, "Cita")
    event = create_arrival_event(db, cita, "CHECKIN_SALA", payload.canal, request, payload.sala_id, current_user.id, payload.dispositivo_id)
    record_audit_event(
        db,
        evento="CHECKIN_SALA",
        entidad="eventos_llegada",
        entidad_id=event.id,
        usuario_id=current_user.id,
        canal=payload.canal,
        ip_origen=client_ip(request),
        valor_despues={"cita_id": str(cita.id)},
    )
    db.commit()
    return CheckinResponse(resultado="VERDE", mensaje="Llegada a sala registrada.", cita_id=cita.id, folio_turno=cita.folio_turno, estado_cita=cita.estado)


@qr_router.post("/validar", response_model=QrValidarResponse)
def validar_qr(payload: QrValidarRequest, request: Request, db: Session = Depends(get_db)):
    result = validate_qr(db, payload.token)
    cita = result.cita
    record_audit_event(
        db,
        evento="QR_VALIDADO",
        entidad="qr_tokens",
        entidad_id=result.qr_token.id if result.qr_token else None,
        canal="API_EXTERNA",
        ip_origen=client_ip(request),
        valor_despues={"valido": result.valid, "resultado": result.status, "cita_id": str(cita.id) if cita else None},
    )
    db.commit()
    return QrValidarResponse(
        valido=result.valid,
        resultado=result.status,
        mensaje=result.message,
        cita_id=cita.id if cita else None,
        folio_turno=cita.folio_turno if cita else None,
        estado_cita=cita.estado if cita else None,
    )


@qr_router.post("/checkin", response_model=CheckinResponse)
def checkin_qr(payload: QrCheckinRequest, request: Request, db: Session = Depends(get_db)):
    result = validate_qr(db, payload.token)
    if not result.valid or result.cita is None:
        record_audit_event(
            db,
            evento="QR_VALIDADO",
            entidad="qr_tokens",
            entidad_id=result.qr_token.id if result.qr_token else None,
            canal=payload.canal,
            ip_origen=client_ip(request),
            valor_despues={"valido": False, "resultado": result.status},
        )
        db.commit()
        return CheckinResponse(resultado="ROJO", mensaje=result.message)

    cita = result.cita
    resultado, mensaje = checkin_window_status(cita, zona_horaria=cita_zona_horaria(db, cita))
    if resultado != "ROJO":
        event = create_arrival_event(db, cita, "CHECKIN_LOBBY", payload.canal, request, payload.sala_id, dispositivo_id=payload.dispositivo_id)
        if result.qr_token is not None:
            result.qr_token.estado = "USADO"
        record_audit_event(
            db,
            evento="CHECKIN_LOBBY",
            entidad="eventos_llegada",
            entidad_id=event.id,
            canal=payload.canal,
            ip_origen=client_ip(request),
            valor_despues={"cita_id": str(cita.id), "resultado": resultado},
        )
    record_audit_event(
        db,
        evento="QR_VALIDADO",
        entidad="qr_tokens",
        entidad_id=result.qr_token.id if result.qr_token else None,
        canal=payload.canal,
        ip_origen=client_ip(request),
        valor_despues={"valido": True, "resultado": resultado, "cita_id": str(cita.id)},
    )
    db.commit()
    db.refresh(cita)
    return CheckinResponse(resultado=resultado, mensaje=mensaje, cita_id=cita.id, folio_turno=cita.folio_turno, estado_cita=cita.estado)
