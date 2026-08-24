from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime
from typing import Any
import unicodedata
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, require_role
from app.api.flow import business_today, cita_search_item, cita_zona_horaria, create_arrival_event, normalized_digits, query_citas
from app.models.flow import Cita, Paciente
from app.models.complejo import Complejo
from app.models.kiosk import Kiosko, PuntoAcceso
from app.models.operational import Piso, Torre
from app.models.usuario import Usuario
from app.schemas.flow import CheckinRequest, CheckinResponse, CitaSearchResult, QrCheckinRequest
from app.schemas.kiosk import (
    KioskoCreate,
    KioskoPacienteOption,
    KioskoPublicConfig,
    KioskoRead,
    KioskoUpdate,
    PuntoAccesoCreate,
    PuntoAccesoRead,
    PuntoAccesoUpdate,
)
from app.services.audit_service import audit_safe_dict, record_audit_event
from app.services.checkin_service import checkin_window_status
from app.services.qr_service import validate_qr

router = APIRouter()
AdminUser = Depends(require_role("ADMIN_SISTEMA", "ADMIN_NEGOCIO"))
TERMINAL_CITA_STATES = ("CANCELADA", "EXPIRADA", "NO_LLEGO")
HOMONYM_FAILURE_MESSAGE = "Intente con su QR o diríjase a recepción"
HOMONYM_CONFIRMATION_MESSAGE = "Capture celular o fecha de nacimiento para confirmar al paciente."


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def exists_or_404(db: Session, model: type, item_id: UUID, label: str) -> object:
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} no encontrado.")
    return item


def merged_value(data: dict, item: object | None, key: str):
    return data[key] if key in data else getattr(item, key, None)


def validate_scope(db: Session, data: dict, item: object | None = None) -> tuple[UUID | None, UUID | None]:
    complejo_id = merged_value(data, item, "complejo_id")
    piso_id = merged_value(data, item, "piso_id")
    if complejo_id is not None:
        exists_or_404(db, Complejo, complejo_id, "Campus")
    if piso_id is not None:
        piso = exists_or_404(db, Piso, piso_id, "Piso")
        if complejo_id is not None and piso.complejo_id != complejo_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El piso no pertenece al campus indicado.")
    return complejo_id, piso_id


def validate_punto(db: Session, data: dict, item: PuntoAcceso | None = None) -> None:
    complejo_id = merged_value(data, item, "complejo_id")
    torre_id = merged_value(data, item, "torre_id")
    piso_id = merged_value(data, item, "piso_id")
    if complejo_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El campus es obligatorio.")
    exists_or_404(db, Complejo, complejo_id, "Campus")
    if torre_id is not None:
        torre = exists_or_404(db, Torre, torre_id, "Torre")
        if torre.complejo_id != complejo_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La torre no pertenece al campus indicado.")
    if piso_id is not None:
        if torre_id is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Seleccione una torre para indicar un piso.")
        piso = exists_or_404(db, Piso, piso_id, "Piso")
        if piso.complejo_id != complejo_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El piso no pertenece al campus indicado.")
        if piso.torre_id != torre_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El piso no pertenece a la torre indicada.")


def validate_kiosko(db: Session, data: dict, item: Kiosko | None = None) -> None:
    complejo_id, _piso_id = validate_scope(db, data, item)
    punto_id = data.get("punto_acceso_id", getattr(item, "punto_acceso_id", None))
    if punto_id is not None:
        punto = exists_or_404(db, PuntoAcceso, punto_id, "Punto de acceso")
        if complejo_id is not None and punto.complejo_id != complejo_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El punto de acceso no pertenece al campus indicado.")
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


def active_kiosko_or_404(db: Session, codigo_dispositivo: str) -> Kiosko:
    kiosko = db.execute(
        select(Kiosko).where(
            Kiosko.codigo_dispositivo == codigo_dispositivo,
            Kiosko.activo.is_(True),
        )
    ).scalar_one_or_none()
    if kiosko is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kiosko no encontrado o inactivo.")
    return kiosko


def touch_kiosko(db: Session, kiosko: Kiosko) -> None:
    kiosko.ultima_conexion = datetime.now(UTC)
    db.commit()
    db.refresh(kiosko)


def active_punto_for_kiosko_or_404(db: Session, kiosko: Kiosko) -> PuntoAcceso:
    punto = db.get(PuntoAcceso, kiosko.punto_acceso_id)
    if punto is None or not punto.activo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Punto de acceso no encontrado o inactivo.")
    if punto.complejo_id != kiosko.complejo_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="El kiosko no pertenece al punto de acceso indicado.")
    return punto


def cita_in_punto_scope(db: Session, cita: Cita, punto: PuntoAcceso) -> bool:
    if cita.fecha_cita != business_today() or cita.complejo_id != punto.complejo_id:
        return False
    if punto.piso_id is not None:
        return cita.piso_id == punto.piso_id
    if punto.torre_id is not None:
        piso = db.get(Piso, cita.piso_id)
        return piso is not None and piso.torre_id == punto.torre_id
    return True


def punto_citas_query(
    db: Session,
    punto: PuntoAcceso,
    *,
    paciente: str | None = None,
    celular: str | None = None,
    fecha_nacimiento: date | None = None,
):
    return query_citas(
        db,
        fecha=business_today(),
        complejo_id=punto.complejo_id,
        torre_id=punto.torre_id,
        piso_id=punto.piso_id,
        paciente=paciente,
        celular=celular,
        fecha_nacimiento=fecha_nacimiento,
    ).where(Cita.estado.notin_(TERMINAL_CITA_STATES))


def remove_accents(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFD", value) if unicodedata.category(char) != "Mn")


def normalize_patient_text(value: str) -> str:
    text = remove_accents(value).lower()
    text = "".join(char if char.isalpha() else " " for char in text)
    return " ".join(text.split())


def patient_lookup_letter_count(value: str) -> int:
    return sum(1 for char in remove_accents(value) if char.isalpha())


def patient_lookup_label(paciente: Paciente) -> str:
    last_names = " ".join(part for part in [paciente.apellido_paterno, paciente.apellido_materno] if part)
    first_names = paciente.nombre_preferido or paciente.nombre or ""
    if last_names and first_names:
        return f"{last_names}, {first_names}"
    return first_names or last_names or paciente.folio_paciente


def patient_identity_key(paciente: Paciente) -> str:
    return normalize_patient_text(
        " ".join(part for part in [paciente.apellido_paterno, paciente.apellido_materno, paciente.nombre or paciente.nombre_preferido] if part)
    )


def patient_matches_terms(paciente: Paciente, query: str) -> bool:
    text = normalize_patient_text(
        " ".join(
            part
            for part in [
                paciente.apellido_paterno,
                paciente.apellido_materno,
                paciente.nombre,
                paciente.nombre_preferido,
                paciente.folio_paciente,
            ]
            if part
        )
    )
    terms = normalize_patient_text(query).split()
    return bool(terms) and all(term in text for term in terms)


def scoped_patients_for_punto(db: Session, punto: PuntoAcceso) -> list[Paciente]:
    query = (
        select(Paciente)
        .join(Cita, Cita.paciente_id == Paciente.id)
        .where(
            Cita.fecha_cita == business_today(),
            Cita.complejo_id == punto.complejo_id,
            Cita.estado.notin_(TERMINAL_CITA_STATES),
            Paciente.activo.is_(True),
            Paciente.marcado_borrado_en.is_(None),
        )
    )
    if punto.piso_id is not None:
        query = query.where(Cita.piso_id == punto.piso_id)
    elif punto.torre_id is not None:
        query = query.where(select(Piso.id).where(Piso.id == Cita.piso_id, Piso.torre_id == punto.torre_id).exists())

    patients: dict[UUID, Paciente] = {}
    for patient in db.execute(query).scalars():
        patients[patient.id] = patient
    return list(patients.values())


def patient_matches_contact(paciente: Paciente, celular: str | None, fecha_nacimiento: date | None) -> bool:
    digits = normalized_digits(celular)
    if digits and normalized_digits(paciente.celular) != digits:
        return False
    if fecha_nacimiento is not None and paciente.fecha_nacimiento != fecha_nacimiento:
        return False
    return digits is not None or fecha_nacimiento is not None


def resolve_kiosko_patient_id(
    db: Session,
    punto: PuntoAcceso,
    paciente_id: UUID,
    celular: str | None,
    fecha_nacimiento: date | None,
) -> UUID:
    selected = db.get(Paciente, paciente_id)
    if selected is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=HOMONYM_FAILURE_MESSAGE)
    scoped_patients = scoped_patients_for_punto(db, punto)
    identity_key = patient_identity_key(selected)
    homonyms = [patient for patient in scoped_patients if patient_identity_key(patient) == identity_key]
    if not any(patient.id == selected.id for patient in homonyms):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=HOMONYM_FAILURE_MESSAGE)
    if len(homonyms) <= 1:
        if (normalized_digits(celular) is not None or fecha_nacimiento is not None) and not patient_matches_contact(
            selected,
            celular,
            fecha_nacimiento,
        ):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=HOMONYM_FAILURE_MESSAGE)
        return selected.id
    if normalized_digits(celular) is None and fecha_nacimiento is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=HOMONYM_CONFIRMATION_MESSAGE)
    matches = [patient for patient in homonyms if patient_matches_contact(patient, celular, fecha_nacimiento)]
    if len(matches) != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=HOMONYM_FAILURE_MESSAGE)
    return matches[0].id


def kiosko_checkin_lobby(
    cita: Cita,
    payload: CheckinRequest,
    request: Request,
    db: Session,
    kiosko: Kiosko,
    *,
    mark_qr_used: Any | None = None,
) -> CheckinResponse:
    if cita.estado in TERMINAL_CITA_STATES:
        kiosko.ultima_conexion = datetime.now(UTC)
        db.commit()
        return CheckinResponse(
            resultado="ROJO",
            mensaje=f"La cita está en estado {cita.estado}.",
            cita_id=cita.id,
            folio_turno=cita.folio_turno,
            estado_cita=cita.estado,
        )
    resultado, mensaje = checkin_window_status(cita, zona_horaria=cita_zona_horaria(db, cita))
    if resultado != "ROJO":
        event = create_arrival_event(
            db,
            cita,
            "CHECKIN_LOBBY",
            payload.canal,
            request,
            payload.sala_id,
            dispositivo_id=payload.dispositivo_id or kiosko.codigo_dispositivo,
        )
        if mark_qr_used is not None:
            mark_qr_used.estado = "USADO"
        record_audit_event(
            db,
            evento="CHECKIN_LOBBY",
            entidad="eventos_llegada",
            entidad_id=event.id,
            canal=payload.canal,
            ip_origen=client_ip(request),
            valor_despues={"cita_id": str(cita.id), "resultado": resultado, "kiosko_id": str(kiosko.id)},
        )
    kiosko.ultima_conexion = datetime.now(UTC)
    db.commit()
    db.refresh(cita)
    return CheckinResponse(resultado=resultado, mensaje=mensaje, cita_id=cita.id, folio_turno=cita.folio_turno, estado_cita=cita.estado)


@router.get("/kioskos/public/{codigo_dispositivo}/config", response_model=KioskoPublicConfig)
def public_kiosko_config(codigo_dispositivo: str, db: Session = Depends(get_db)) -> KioskoPublicConfig:
    kiosko = active_kiosko_or_404(db, codigo_dispositivo)
    touch_kiosko(db, kiosko)
    return KioskoPublicConfig(
        codigo_dispositivo=kiosko.codigo_dispositivo,
        nombre=kiosko.nombre,
        polling_interval_seconds=kiosko.polling_interval_seconds,
        color_fondo=kiosko.color_fondo,
        color_texto=kiosko.color_texto,
        color_primario=kiosko.color_primario,
        color_acento=kiosko.color_acento,
    )


@router.get("/kioskos/public/{codigo_dispositivo}/pacientes/buscar", response_model=list[KioskoPacienteOption])
def public_kiosko_buscar_pacientes(
    codigo_dispositivo: str,
    q: str = Query(min_length=1),
    db: Session = Depends(get_db),
) -> list[KioskoPacienteOption]:
    kiosko = active_kiosko_or_404(db, codigo_dispositivo)
    punto = active_punto_for_kiosko_or_404(db, kiosko)
    if patient_lookup_letter_count(q) < 4:
        return []
    matched_patients = [patient for patient in scoped_patients_for_punto(db, punto) if patient_matches_terms(patient, q)]
    identity_counts = Counter(patient_identity_key(patient) for patient in matched_patients)
    matched_patients.sort(key=lambda patient: (normalize_patient_text(patient_lookup_label(patient)), str(patient.id)))
    touch_kiosko(db, kiosko)
    return [
        KioskoPacienteOption(
            id=patient.id,
            label=patient_lookup_label(patient),
            homonimo=identity_counts[patient_identity_key(patient)] > 1,
        )
        for patient in matched_patients[:20]
    ]


@router.get("/kioskos/public/{codigo_dispositivo}/citas/buscar", response_model=list[CitaSearchResult])
def public_kiosko_buscar_citas(
    codigo_dispositivo: str,
    paciente: str = Query(min_length=1),
    paciente_id: UUID | None = None,
    celular: str | None = None,
    fecha_nacimiento: date | None = None,
    db: Session = Depends(get_db),
) -> list[CitaSearchResult]:
    kiosko = active_kiosko_or_404(db, codigo_dispositivo)
    punto = active_punto_for_kiosko_or_404(db, kiosko)
    query = punto_citas_query(db, punto)
    if paciente_id is not None:
        scoped_patient_id = resolve_kiosko_patient_id(db, punto, paciente_id, celular, fecha_nacimiento)
        query = query.where(Cita.paciente_id == scoped_patient_id)
    else:
        matching_patients = [patient for patient in scoped_patients_for_punto(db, punto) if patient_matches_terms(patient, paciente)]
        if normalized_digits(celular) is not None or fecha_nacimiento is not None:
            matching_patients = [patient for patient in matching_patients if patient_matches_contact(patient, celular, fecha_nacimiento)]
        if not matching_patients:
            touch_kiosko(db, kiosko)
            return []
        query = query.where(Cita.paciente_id.in_([patient.id for patient in matching_patients]))
    rows = list(
        db.execute(
            query.limit(20)
        )
        .scalars()
    )
    touch_kiosko(db, kiosko)
    return [cita_search_item(db, row) for row in rows]


@router.post("/kioskos/public/{codigo_dispositivo}/citas/{cita_id}/checkin-lobby", response_model=CheckinResponse)
def public_kiosko_checkin_lobby_cita(
    codigo_dispositivo: str,
    cita_id: UUID,
    payload: CheckinRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> CheckinResponse:
    kiosko = active_kiosko_or_404(db, codigo_dispositivo)
    punto = active_punto_for_kiosko_or_404(db, kiosko)
    cita = exists_or_404(db, Cita, cita_id, "Cita")
    if not cita_in_punto_scope(db, cita, punto):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=HOMONYM_FAILURE_MESSAGE)
    return kiosko_checkin_lobby(cita, payload, request, db, kiosko)


@router.post("/kioskos/public/{codigo_dispositivo}/qr/checkin", response_model=CheckinResponse)
def public_kiosko_checkin_qr(
    codigo_dispositivo: str,
    payload: QrCheckinRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> CheckinResponse:
    kiosko = active_kiosko_or_404(db, codigo_dispositivo)
    punto = active_punto_for_kiosko_or_404(db, kiosko)
    result = validate_qr(db, payload.token)
    if not result.valid or result.cita is None:
        record_audit_event(
            db,
            evento="QR_VALIDADO",
            entidad="qr_tokens",
            entidad_id=result.qr_token.id if result.qr_token else None,
            canal=payload.canal,
            ip_origen=client_ip(request),
            valor_despues={"valido": False, "resultado": result.status, "kiosko_id": str(kiosko.id)},
        )
        kiosko.ultima_conexion = datetime.now(UTC)
        db.commit()
        return CheckinResponse(resultado="ROJO", mensaje=result.message)
    if not cita_in_punto_scope(db, result.cita, punto):
        record_audit_event(
            db,
            evento="QR_VALIDADO",
            entidad="qr_tokens",
            entidad_id=result.qr_token.id if result.qr_token else None,
            canal=payload.canal,
            ip_origen=client_ip(request),
            valor_despues={"valido": False, "resultado": "FUERA_DE_ALCANCE", "cita_id": str(result.cita.id), "kiosko_id": str(kiosko.id)},
        )
        kiosko.ultima_conexion = datetime.now(UTC)
        db.commit()
        return CheckinResponse(resultado="ROJO", mensaje=HOMONYM_FAILURE_MESSAGE)
    record_audit_event(
        db,
        evento="QR_VALIDADO",
        entidad="qr_tokens",
        entidad_id=result.qr_token.id if result.qr_token else None,
        canal=payload.canal,
        ip_origen=client_ip(request),
        valor_despues={"valido": True, "resultado": result.status, "cita_id": str(result.cita.id), "kiosko_id": str(kiosko.id)},
    )
    return kiosko_checkin_lobby(result.cita, payload, request, db, kiosko, mark_qr_used=result.qr_token)


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
