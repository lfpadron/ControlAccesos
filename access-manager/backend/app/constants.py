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
    "auditoria",
)
