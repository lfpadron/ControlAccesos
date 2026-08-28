from __future__ import annotations

TURNO_TEMPLATE_PATIENT_CONSULTORIO = "PACIENTE_CONSULTORIO"
TURNO_TEMPLATE_TURNO_PATIENT_CONSULTORIO = "TURNO_PACIENTE_CONSULTORIO"
TURNO_TEMPLATE_PATIENT_TURNO_CONSULTORIO = "PACIENTE_TURNO_CONSULTORIO"
TURNO_TEMPLATE_TURNO_CONSULTORIO = "TURNO_CONSULTORIO"

TURNO_TEMPLATE_DEFAULT = TURNO_TEMPLATE_PATIENT_CONSULTORIO
TURNO_TEMPLATE_CHOICES = (
    TURNO_TEMPLATE_PATIENT_CONSULTORIO,
    TURNO_TEMPLATE_TURNO_PATIENT_CONSULTORIO,
    TURNO_TEMPLATE_PATIENT_TURNO_CONSULTORIO,
    TURNO_TEMPLATE_TURNO_CONSULTORIO,
)

DEFAULT_INITIAL_SCREEN = "perfil"
MENU_SCREEN_KEYS = (
    "dashboard",
    "perfil",
    "instituciones",
    "campus",
    "torres",
    "pisos",
    "salas-espera",
    "consultorios",
    "usuarios",
    "busqueda-usuarios",
    "roles",
    "usuario-roles",
    "plantilla-turnos",
    "pacientes",
    "citas",
    "citas-hoy",
    "estado-medico",
    "recepcion",
    "checkin-qr",
    "contactos-institucionales",
    "asignaciones",
    "clusters-turnos",
    "consulta-clusters-consultorios",
    "pantallas-turnos",
    "consulta-clusters-pantallas",
    "kioskos",
    "turnos-llamados",
    "reportes",
    "reportes-medicos",
    "reportes-recepcion",
    "auditoria",
)

APP_PERMISSION_KEYS = (
    "app-qr",
    "app-medicos",
)

PERMISSION_KEYS = MENU_SCREEN_KEYS + APP_PERMISSION_KEYS

ROLE_DEFAULT_PERMISSIONS = {
    "RECEPCIONISTA": {
        "recepcion": "editar",
        "checkin-qr": "editar",
        "app-qr": "editar",
        "reportes-recepcion": "consultar",
    },
    "MEDICO": {
        "pacientes": "consultar",
        "citas": "consultar",
        "estado-medico": "editar",
        "reportes-medicos": "consultar",
        "app-medicos": "editar",
    },
}


def default_permissions_for_role(codigo: str) -> dict[str, str]:
    if codigo == "ADMIN_SISTEMA":
        return {screen: "editar" for screen in PERMISSION_KEYS}
    return dict(ROLE_DEFAULT_PERMISSIONS.get(codigo, {}))
