from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, require_role
from app.models.auditoria import Auditoria
from app.models.complejo import Complejo
from app.models.display import PantallaTurnos, PantallaTurnosCluster
from app.models.institucion import Institucion
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
from app.schemas.operational import (
    AsignacionMedicoConsultorioCreate,
    AsignacionMedicoConsultorioRead,
    AsignacionMedicoConsultorioUpdate,
    AsignacionOperadorCreate,
    AsignacionOperadorRead,
    AsignacionOperadorUpdate,
    AuditoriaRead,
    ClusterTurnosCreate,
    ClusterTurnosRead,
    ClusterTurnosUpdate,
    ConsultorioCreate,
    ConsultorioRead,
    ConsultorioUpdate,
    MedicoCreate,
    MedicoRead,
    MedicoUpdate,
    OperadorCreate,
    OperadorRead,
    OperadorUpdate,
    PisoCreate,
    PisoRead,
    PisoUpdate,
    RoleCreate,
    RoleRead,
    RoleUpdate,
    SalaEsperaCreate,
    SalaEsperaRead,
    SalaEsperaUpdate,
    UsuarioRolCreate,
    UsuarioRolRead,
    UsuarioRolUpdate,
)
from app.schemas.usuario import UsuarioCreate, UsuarioRead, UsuarioUpdate
from app.services.audit_service import audit_safe_dict, record_audit_event

AdminUser = Depends(require_role("ADMIN_SISTEMA", "ADMIN_NEGOCIO"))


@dataclass(frozen=True)
class CrudConfig:
    model: type
    create_schema: type[BaseModel]
    update_schema: type[BaseModel]
    read_schema: type[BaseModel]
    entity: str
    create_event: str
    edit_event: str
    order_field: str = "created_at"
    active_field: str = "activo"
    active_value: Any = True
    inactive_value: Any = False
    validator: Callable[[Session, dict[str, Any], object | None], None] | None = None
    prepare_create: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    prepare_update: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    relation_fields: tuple[str, ...] = ()
    relation_handler: Callable[[Session, object, dict[str, Any]], None] | None = None
    response_factory: Callable[[Session, object], object] | None = None
    audit_extra_factory: Callable[[Session, object], dict[str, Any]] | None = None


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def exists_or_404(db: Session, model: type, item_id: UUID, label: str) -> object:
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} no encontrado.")
    return item


def validate_payload(schema: type[BaseModel], payload_data: dict[str, Any]) -> BaseModel:
    try:
        return schema.model_validate(payload_data)
    except ValidationError as exc:
        detail = [
            {
                "loc": list(error.get("loc", ())),
                "msg": str(error.get("msg", "Entrada inválida")),
                "type": str(error.get("type", "value_error")),
            }
            for error in exc.errors()
        ]
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail) from exc


def validate_date_range(data: dict[str, Any], item: object | None = None) -> None:
    fecha_inicio = data.get("fecha_inicio", getattr(item, "fecha_inicio", None))
    fecha_fin = data.get("fecha_fin", getattr(item, "fecha_fin", None))
    if fecha_inicio is not None and fecha_fin is not None and fecha_fin < fecha_inicio:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="fecha_fin no puede ser menor que fecha_inicio.")


def validate_unique_role_code(db: Session, data: dict[str, Any], item: object | None = None) -> None:
    codigo = data.get("codigo")
    if codigo is None:
        return
    query = select(Role).where(Role.codigo == codigo)
    if item is not None:
        query = query.where(Role.id != item.id)
    if db.execute(query).scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El código de rol ya existe.")


def validate_unique_email(db: Session, data: dict[str, Any], item: object | None = None) -> None:
    email = data.get("email")
    if email is None:
        return
    normalized_email = str(email).strip().lower()
    query = select(Usuario).where(func.lower(Usuario.email) == normalized_email)
    if item is not None:
        query = query.where(Usuario.id != item.id)
    if db.execute(query).scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya existe.")


def validate_usuario_rol(db: Session, data: dict[str, Any], _item: object | None = None) -> None:
    usuario_id = data.get("usuario_id")
    rol_id = data.get("rol_id")
    institucion_id = data.get("institucion_id")
    complejo_id = data.get("complejo_id")
    if usuario_id is not None:
        exists_or_404(db, Usuario, usuario_id, "Usuario")
    if rol_id is not None:
        exists_or_404(db, Role, rol_id, "Rol")
    if institucion_id is not None:
        exists_or_404(db, Institucion, institucion_id, "Institución")
    if complejo_id is not None:
        complejo = exists_or_404(db, Complejo, complejo_id, "Complejo")
        if institucion_id is not None and complejo.institucion_id != institucion_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El complejo no pertenece a la institución indicada.")


def validate_piso(db: Session, data: dict[str, Any], _item: object | None = None) -> None:
    if data.get("complejo_id") is not None:
        exists_or_404(db, Complejo, data["complejo_id"], "Complejo")


def validate_sala_or_consultorio(db: Session, data: dict[str, Any], item: object | None = None) -> None:
    complejo_id = data.get("complejo_id", getattr(item, "complejo_id", None))
    piso_id = data.get("piso_id", getattr(item, "piso_id", None))
    if complejo_id is not None:
        exists_or_404(db, Complejo, complejo_id, "Complejo")
    if piso_id is not None:
        piso = exists_or_404(db, Piso, piso_id, "Piso")
        if complejo_id is not None and piso.complejo_id != complejo_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El piso no pertenece al complejo indicado.")


def validate_cluster_turnos(db: Session, data: dict[str, Any], item: object | None = None) -> None:
    complejo_id = data.get("complejo_id", getattr(item, "complejo_id", None))
    piso_id = data.get("piso_id", getattr(item, "piso_id", None))
    if complejo_id is not None:
        exists_or_404(db, Complejo, complejo_id, "Complejo")
    if piso_id is not None:
        piso = exists_or_404(db, Piso, piso_id, "Piso")
        if complejo_id is not None and piso.complejo_id != complejo_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El piso no pertenece al complejo indicado.")


def cluster_ids_for_consultorio(db: Session, consultorio_id: UUID) -> list[UUID]:
    return list(
        db.execute(select(ConsultorioCluster.cluster_id).where(ConsultorioCluster.consultorio_id == consultorio_id)).scalars()
    )


def validate_clusters_for_scope(db: Session, cluster_ids: list[UUID], complejo_id: UUID, piso_id: UUID) -> None:
    if not cluster_ids:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Debe asignar al menos un clúster.")
    clusters = list(db.execute(select(ClusterTurnos).where(ClusterTurnos.id.in_(cluster_ids))).scalars())
    found = {cluster.id for cluster in clusters}
    missing = [str(cluster_id) for cluster_id in cluster_ids if cluster_id not in found]
    if missing:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Clústers no encontrados: {', '.join(missing)}")
    for cluster in clusters:
        if cluster.complejo_id != complejo_id or cluster.piso_id != piso_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Los clústers deben pertenecer al mismo complejo y piso del consultorio.",
            )
    if (
        db.execute(
            select(PantallaTurnosCluster)
            .join(PantallaTurnos, PantallaTurnos.id == PantallaTurnosCluster.pantalla_id)
            .where(PantallaTurnos.activa.is_(True), PantallaTurnosCluster.cluster_id.in_(cluster_ids))
            .limit(1)
        ).first()
        is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Debe seleccionar al menos un clúster con una pantalla de turnos activa.",
        )


def consultorio_has_display_coverage(db: Session, consultorio_id: UUID) -> bool:
    cluster_ids = cluster_ids_for_consultorio(db, consultorio_id)
    if not cluster_ids:
        return False
    return (
        db.execute(
            select(PantallaTurnosCluster)
            .join(PantallaTurnos, PantallaTurnos.id == PantallaTurnosCluster.pantalla_id)
            .where(
                PantallaTurnos.activa.is_(True),
                PantallaTurnosCluster.cluster_id.in_(cluster_ids),
            )
            .limit(1)
        ).first()
        is not None
    )


def ensure_consultorio_display_coverage(db: Session, consultorio_id: UUID) -> None:
    if not consultorio_has_display_coverage(db, consultorio_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El consultorio debe estar asociado a por lo menos un clúster con una pantalla de turnos activa.",
        )


def replace_consultorio_clusters(db: Session, item: object, relation_data: dict[str, Any]) -> None:
    if "cluster_ids" not in relation_data:
        return
    db.query(ConsultorioCluster).filter(ConsultorioCluster.consultorio_id == item.id).delete()
    for cluster_id in relation_data["cluster_ids"] or []:
        db.add(ConsultorioCluster(consultorio_id=item.id, cluster_id=cluster_id))


def consultorio_response(db: Session, item: object) -> ConsultorioRead:
    return ConsultorioRead(
        id=item.id,
        complejo_id=item.complejo_id,
        piso_id=item.piso_id,
        codigo=item.codigo,
        nombre_visible=item.nombre_visible,
        instrucciones_acceso=item.instrucciones_acceso,
        cluster_ids=cluster_ids_for_consultorio(db, item.id),
        activo=item.activo,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def consultorio_audit_extra(db: Session, item: object) -> dict[str, Any]:
    return {"cluster_ids": [str(cluster_id) for cluster_id in cluster_ids_for_consultorio(db, item.id)]}


def validate_consultorio(db: Session, data: dict[str, Any], item: object | None = None) -> None:
    validate_sala_or_consultorio(db, data, item)
    codigo = data.get("codigo", getattr(item, "codigo", None))
    complejo_id = data.get("complejo_id", getattr(item, "complejo_id", None))
    piso_id = data.get("piso_id", getattr(item, "piso_id", None))
    cluster_ids = data.get("cluster_ids")
    if codigo is None or complejo_id is None:
        return
    if item is None and cluster_ids is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Debe asignar al menos un clúster.")
    if cluster_ids is None and item is not None:
        cluster_ids = cluster_ids_for_consultorio(db, item.id)
    if piso_id is not None:
        validate_clusters_for_scope(db, cluster_ids or [], complejo_id, piso_id)
    query = select(Consultorio).where(Consultorio.complejo_id == complejo_id, Consultorio.codigo == codigo)
    if item is not None:
        query = query.where(Consultorio.id != item.id)
    if db.execute(query).scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El código de consultorio ya existe en este complejo.")


def validate_medico(db: Session, data: dict[str, Any], _item: object | None = None) -> None:
    if data.get("usuario_id") is not None:
        exists_or_404(db, Usuario, data["usuario_id"], "Usuario")


def validate_operador(db: Session, data: dict[str, Any], _item: object | None = None) -> None:
    if data.get("usuario_id") is not None:
        exists_or_404(db, Usuario, data["usuario_id"], "Usuario")


def validate_asignacion_medico_consultorio(db: Session, data: dict[str, Any], item: object | None = None) -> None:
    validate_date_range(data, item)
    if data.get("medico_id") is not None:
        exists_or_404(db, Medico, data["medico_id"], "Médico")
    consultorio_id = data.get("consultorio_id", getattr(item, "consultorio_id", None))
    if consultorio_id is not None:
        exists_or_404(db, Consultorio, consultorio_id, "Consultorio")
        ensure_consultorio_display_coverage(db, consultorio_id)


def validate_asignacion_operador(db: Session, data: dict[str, Any], item: object | None = None) -> None:
    validate_date_range(data, item)
    operador_id = data.get("operador_id", getattr(item, "operador_id", None))
    medico_id = data.get("medico_id", getattr(item, "medico_id", None))
    consultorio_id = data.get("consultorio_id", getattr(item, "consultorio_id", None))
    complejo_id = data.get("complejo_id", getattr(item, "complejo_id", None))
    if medico_id is None and consultorio_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Debe indicar médico o consultorio para la asignación.")
    if operador_id is not None:
        exists_or_404(db, Operador, operador_id, "Operador")
    if medico_id is not None:
        exists_or_404(db, Medico, medico_id, "Médico")
    if complejo_id is not None:
        exists_or_404(db, Complejo, complejo_id, "Complejo")
    if consultorio_id is not None:
        consultorio = exists_or_404(db, Consultorio, consultorio_id, "Consultorio")
        if complejo_id is not None and consultorio.complejo_id != complejo_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El consultorio no pertenece al complejo indicado.")


def prepare_usuario_create(data: dict[str, Any]) -> dict[str, Any]:
    password = data.pop("password")
    data["email"] = str(data["email"]).strip().lower()
    data["password_hash"] = hash_password(password)
    return data


def prepare_usuario_update(data: dict[str, Any]) -> dict[str, Any]:
    password = data.pop("password", None)
    if data.get("email") is not None:
        data["email"] = str(data["email"]).strip().lower()
    if password:
        data["password_hash"] = hash_password(password)
    return data


def create_crud_router(config: CrudConfig) -> APIRouter:
    router = APIRouter()

    @router.get("", response_model=list[config.read_schema])
    def list_items(
        db: Session = Depends(get_db),
        _current_user: Usuario = AdminUser,
    ) -> list:
        order_column = getattr(config.model, config.order_field)
        items = list(db.execute(select(config.model).order_by(order_column)).scalars())
        if config.response_factory:
            return [config.response_factory(db, item) for item in items]
        return items

    @router.get("/{item_id}", response_model=config.read_schema)
    def get_item(
        item_id: UUID,
        db: Session = Depends(get_db),
        _current_user: Usuario = AdminUser,
    ) -> object:
        item = exists_or_404(db, config.model, item_id, config.entity)
        return config.response_factory(db, item) if config.response_factory else item

    @router.post("", response_model=config.read_schema, status_code=status.HTTP_201_CREATED)
    def create_item(
        request: Request,
        payload_data: dict[str, Any] = Body(...),
        db: Session = Depends(get_db),
        current_user: Usuario = AdminUser,
    ) -> object:
        payload = validate_payload(config.create_schema, payload_data)
        data = payload.model_dump()
        if config.validator:
            config.validator(db, data, None)
        relation_data = {field: data.pop(field) for field in config.relation_fields if field in data}
        if config.prepare_create:
            data = config.prepare_create(data)
        item = config.model(**data)
        db.add(item)
        db.flush()
        if config.relation_handler:
            config.relation_handler(db, item, relation_data)
            db.flush()
        after_extra = config.audit_extra_factory(db, item) if config.audit_extra_factory else {}
        record_audit_event(
            db,
            evento=config.create_event,
            entidad=config.entity,
            entidad_id=item.id,
            usuario_id=current_user.id,
            canal="WEB",
            ip_origen=client_ip(request),
            valor_despues={**audit_safe_dict(item), **after_extra},
        )
        db.commit()
        db.refresh(item)
        return config.response_factory(db, item) if config.response_factory else item

    @router.put("/{item_id}", response_model=config.read_schema)
    @router.patch("/{item_id}", response_model=config.read_schema)
    def update_item(
        item_id: UUID,
        request: Request,
        payload_data: dict[str, Any] = Body(...),
        db: Session = Depends(get_db),
        current_user: Usuario = AdminUser,
    ) -> object:
        item = exists_or_404(db, config.model, item_id, config.entity)
        before_extra = config.audit_extra_factory(db, item) if config.audit_extra_factory else {}
        before = {**audit_safe_dict(item), **before_extra}
        payload = validate_payload(config.update_schema, payload_data)
        data = payload.model_dump(exclude_unset=True)
        if config.prepare_update:
            data = config.prepare_update(data)
        if config.validator:
            config.validator(db, data, item)
        relation_data = {field: data.pop(field) for field in config.relation_fields if field in data}
        for key, value in data.items():
            setattr(item, key, value)
        db.flush()
        if config.relation_handler:
            config.relation_handler(db, item, relation_data)
            db.flush()
        after_extra = config.audit_extra_factory(db, item) if config.audit_extra_factory else {}
        record_audit_event(
            db,
            evento=config.edit_event,
            entidad=config.entity,
            entidad_id=item.id,
            usuario_id=current_user.id,
            canal="WEB",
            ip_origen=client_ip(request),
            valor_antes=before,
            valor_despues={**audit_safe_dict(item), **after_extra},
        )
        db.commit()
        db.refresh(item)
        return config.response_factory(db, item) if config.response_factory else item

    @router.patch("/{item_id}/activar", response_model=config.read_schema)
    @router.post("/{item_id}/activar", response_model=config.read_schema)
    def activate_item(
        item_id: UUID,
        request: Request,
        db: Session = Depends(get_db),
        current_user: Usuario = AdminUser,
    ) -> object:
        return set_active_state(item_id, True, request, db, current_user)

    @router.patch("/{item_id}/desactivar", response_model=config.read_schema)
    @router.post("/{item_id}/desactivar", response_model=config.read_schema)
    def deactivate_item(
        item_id: UUID,
        request: Request,
        db: Session = Depends(get_db),
        current_user: Usuario = AdminUser,
    ) -> object:
        return set_active_state(item_id, False, request, db, current_user)

    def set_active_state(
        item_id: UUID,
        enabled: bool,
        request: Request,
        db: Session,
        current_user: Usuario,
    ) -> object:
        item = exists_or_404(db, config.model, item_id, config.entity)
        before_extra = config.audit_extra_factory(db, item) if config.audit_extra_factory else {}
        before = {**audit_safe_dict(item), **before_extra}
        setattr(item, config.active_field, config.active_value if enabled else config.inactive_value)
        db.flush()
        after_extra = config.audit_extra_factory(db, item) if config.audit_extra_factory else {}
        record_audit_event(
            db,
            evento=config.edit_event,
            entidad=config.entity,
            entidad_id=item.id,
            usuario_id=current_user.id,
            canal="WEB",
            ip_origen=client_ip(request),
            valor_antes=before,
            valor_despues={**audit_safe_dict(item), **after_extra},
        )
        db.commit()
        db.refresh(item)
        return config.response_factory(db, item) if config.response_factory else item

    return router


roles_router = create_crud_router(
    CrudConfig(Role, RoleCreate, RoleUpdate, RoleRead, "roles", "ROL_CREADO", "ROL_EDITADO", "codigo", validator=validate_unique_role_code)
)
usuarios_router = create_crud_router(
    CrudConfig(
        Usuario,
        UsuarioCreate,
        UsuarioUpdate,
        UsuarioRead,
        "usuarios",
        "USUARIO_CREADO",
        "USUARIO_EDITADO",
        "email",
        "estado",
        "ACTIVO",
        "INACTIVO",
        validate_unique_email,
        prepare_usuario_create,
        prepare_usuario_update,
    )
)
usuario_roles_router = create_crud_router(
    CrudConfig(UsuarioRol, UsuarioRolCreate, UsuarioRolUpdate, UsuarioRolRead, "usuario_roles", "ROL_ASIGNADO", "ROL_ASIGNADO_EDITADO", "created_at", validator=validate_usuario_rol)
)
pisos_router = create_crud_router(
    CrudConfig(Piso, PisoCreate, PisoUpdate, PisoRead, "pisos", "PISO_CREADO", "PISO_EDITADO", "numero", validator=validate_piso)
)
clusters_turnos_router = create_crud_router(
    CrudConfig(
        ClusterTurnos,
        ClusterTurnosCreate,
        ClusterTurnosUpdate,
        ClusterTurnosRead,
        "clusters_turnos",
        "CLUSTER_TURNOS_CREADO",
        "CLUSTER_TURNOS_EDITADO",
        "nombre",
        validator=validate_cluster_turnos,
    )
)
salas_espera_router = create_crud_router(
    CrudConfig(SalaEspera, SalaEsperaCreate, SalaEsperaUpdate, SalaEsperaRead, "salas_espera", "SALA_CREADA", "SALA_EDITADA", "nombre", "activa", True, False, validate_sala_or_consultorio)
)
consultorios_router = create_crud_router(
    CrudConfig(
        Consultorio,
        ConsultorioCreate,
        ConsultorioUpdate,
        ConsultorioRead,
        "consultorios",
        "CONSULTORIO_CREADO",
        "CONSULTORIO_EDITADO",
        "codigo",
        validator=validate_consultorio,
        relation_fields=("cluster_ids",),
        relation_handler=replace_consultorio_clusters,
        response_factory=consultorio_response,
        audit_extra_factory=consultorio_audit_extra,
    )
)
medicos_router = create_crud_router(
    CrudConfig(Medico, MedicoCreate, MedicoUpdate, MedicoRead, "medicos", "MEDICO_CREADO", "MEDICO_EDITADO", "apellidos", validator=validate_medico)
)
operadores_router = create_crud_router(
    CrudConfig(Operador, OperadorCreate, OperadorUpdate, OperadorRead, "operadores", "OPERADOR_CREADO", "OPERADOR_EDITADO", "created_at", validator=validate_operador)
)
asignaciones_medico_consultorio_router = create_crud_router(
    CrudConfig(
        AsignacionMedicoConsultorio,
        AsignacionMedicoConsultorioCreate,
        AsignacionMedicoConsultorioUpdate,
        AsignacionMedicoConsultorioRead,
        "asignaciones_medico_consultorio",
        "ASIGNACION_MEDICO_CONSULTORIO_CREADA",
        "ASIGNACION_MEDICO_CONSULTORIO_EDITADA",
        "fecha_inicio",
        validator=validate_asignacion_medico_consultorio,
    )
)
asignaciones_operador_router = create_crud_router(
    CrudConfig(
        AsignacionOperador,
        AsignacionOperadorCreate,
        AsignacionOperadorUpdate,
        AsignacionOperadorRead,
        "asignaciones_operador",
        "ASIGNACION_OPERADOR_CREADA",
        "ASIGNACION_OPERADOR_EDITADA",
        "fecha_inicio",
        validator=validate_asignacion_operador,
    )
)

auditoria_router = APIRouter()


@auditoria_router.get("", response_model=list[AuditoriaRead])
def list_auditoria(
    db: Session = Depends(get_db),
    _current_user: Usuario = AdminUser,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[Auditoria]:
    return list(db.execute(select(Auditoria).order_by(Auditoria.created_at.desc()).limit(limit)).scalars())
