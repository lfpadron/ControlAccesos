import type { AccessLevel, Usuario } from './api/client';

export const accessLevels: Array<{ value: AccessLevel; label: string }> = [
  { value: 'sin', label: 'Sin acceso' },
  { value: 'consultar', label: 'Consultar' },
  { value: 'editar', label: 'Editar' },
];

export type ScreenDefinition = {
  key: string;
  label: string;
  path: string;
};

export type AccessDefinition = {
  key: string;
  label: string;
  path?: string;
  kind: 'screen' | 'app';
  allowedLevels?: AccessLevel[];
};

export const screens: ScreenDefinition[] = [
  { key: 'dashboard', label: 'Dashboard', path: '/dashboard' },
  { key: 'perfil', label: 'Perfil', path: '/perfil' },
  { key: 'instituciones', label: 'Instituciones', path: '/instituciones' },
  { key: 'campus', label: 'Campus', path: '/complejos' },
  { key: 'torres', label: 'Torres', path: '/torres' },
  { key: 'pisos', label: 'Pisos', path: '/pisos' },
  { key: 'salas-espera', label: 'Salas de espera', path: '/salas-espera' },
  { key: 'consultorios', label: 'Consultorios', path: '/consultorios' },
  { key: 'usuarios', label: 'Usuarios', path: '/usuarios' },
  { key: 'busqueda-usuarios', label: 'Búsqueda de usuarios', path: '/busqueda-usuarios' },
  { key: 'roles', label: 'Roles', path: '/roles' },
  { key: 'usuario-roles', label: 'Asignación de usuarios', path: '/usuario-roles' },
  { key: 'plantilla-turnos', label: 'Preferencias del médico', path: '/plantilla-turnos' },
  { key: 'pacientes', label: 'Pacientes', path: '/pacientes' },
  { key: 'citas', label: 'Citas', path: '/citas' },
  { key: 'citas-hoy', label: 'Citas de hoy', path: '/citas/hoy' },
  { key: 'estado-medico', label: 'Estado del médico', path: '/estado-medico' },
  { key: 'recepcion', label: 'Recepción', path: '/recepcion' },
  { key: 'checkin-qr', label: 'Checkin QR', path: '/checkin-qr' },
  { key: 'contactos-institucionales', label: 'Contactos institucionales', path: '/contactos-institucionales' },
  { key: 'asignaciones', label: 'Asignaciones', path: '/asignaciones' },
  { key: 'clusters-turnos', label: 'Clústers', path: '/clusters-turnos' },
  { key: 'consulta-clusters-consultorios', label: 'Consulta de clústers', path: '/consulta-clusters-consultorios' },
  { key: 'pantallas-turnos', label: 'Pantallas de turnos', path: '/pantallas-turnos' },
  { key: 'consulta-clusters-pantallas', label: 'Consulta de clúster y pantallas', path: '/consulta-clusters-pantallas' },
  { key: 'kioskos', label: 'Kioskos', path: '/kioskos' },
  { key: 'turnos-llamados', label: 'Turnos llamados', path: '/turnos-llamados' },
  { key: 'reportes', label: 'Reportes', path: '/reportes' },
  { key: 'reportes-medicos', label: 'Reportes médicos', path: '/reportes/medicos' },
  { key: 'reportes-recepcion', label: 'Reportes recepción', path: '/reportes/recepcion' },
  { key: 'auditoria', label: 'Auditoría', path: '/auditoria' },
];

export const appAccessDefinitions: AccessDefinition[] = [
  { key: 'app-qr', label: 'App de QR', kind: 'app', allowedLevels: ['sin', 'editar'] },
  { key: 'app-medicos', label: 'App médicos', kind: 'app', allowedLevels: ['sin', 'editar'] },
];

export const accessDefinitions: AccessDefinition[] = [
  ...screens.map((screen) => ({ ...screen, kind: 'screen' as const })),
  ...appAccessDefinitions,
];

export const screenByPath = new Map(screens.map((screen) => [screen.path, screen]));
export const screenByKey = new Map(screens.map((screen) => [screen.key, screen]));
export const DEFAULT_INITIAL_SCREEN = 'perfil';

export function initialPathForUser(user: Usuario | null) {
  const screen = screenByKey.get(user?.pantalla_inicial || DEFAULT_INITIAL_SCREEN);
  return screen?.path ?? '/perfil';
}

export function accessForPath(user: Usuario | null, path: string): AccessLevel {
  if (!user?.permisos) return 'editar';
  const screen = screenByPath.get(path);
  if (!screen) return 'editar';
  return user.permisos[screen.key] ?? 'sin';
}

export function canAccessPath(user: Usuario | null, path: string) {
  return accessForPath(user, path) !== 'sin';
}
