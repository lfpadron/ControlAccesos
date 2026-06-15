from __future__ import annotations

from fastapi import APIRouter

from app.api import auth, complejos, contactos, display, flow, health, instituciones, kiosks, operational

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(instituciones.router, prefix="/instituciones", tags=["instituciones"])
api_router.include_router(complejos.router, prefix="/complejos", tags=["complejos"])
api_router.include_router(flow.pacientes_router, prefix="/pacientes", tags=["pacientes"])
api_router.include_router(flow.citas_router, prefix="/citas", tags=["citas"])
api_router.include_router(flow.qr_router, prefix="/qr", tags=["qr"])
api_router.include_router(contactos.router, prefix="/contactos-institucionales", tags=["contactos-institucionales"])
api_router.include_router(kiosks.router, tags=["kiosks"])
api_router.include_router(operational.roles_router, prefix="/roles", tags=["roles"])
api_router.include_router(operational.usuarios_router, prefix="/usuarios", tags=["usuarios"])
api_router.include_router(operational.usuario_roles_router, prefix="/usuario-roles", tags=["usuario-roles"])
api_router.include_router(operational.pisos_router, prefix="/pisos", tags=["pisos"])
api_router.include_router(operational.salas_espera_router, prefix="/salas-espera", tags=["salas-espera"])
api_router.include_router(operational.clusters_turnos_router, prefix="/clusters-turnos", tags=["clusters-turnos"])
api_router.include_router(operational.consultorios_router, prefix="/consultorios", tags=["consultorios"])
api_router.include_router(operational.medicos_router, prefix="/medicos", tags=["medicos"])
api_router.include_router(operational.operadores_router, prefix="/operadores", tags=["operadores"])
api_router.include_router(
    operational.asignaciones_medico_consultorio_router,
    prefix="/asignaciones-medico-consultorio",
    tags=["asignaciones-medico-consultorio"],
)
api_router.include_router(
    operational.asignaciones_operador_router,
    prefix="/asignaciones-operador",
    tags=["asignaciones-operador"],
)
api_router.include_router(operational.auditoria_router, prefix="/auditoria", tags=["auditoria"])
api_router.include_router(display.router, tags=["display"])
