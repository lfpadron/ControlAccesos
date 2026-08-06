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

export const screens: ScreenDefinition[] = [
  { key: 'dashboard', label: 'Dashboard', path: '/dashboard' },
  { key: 'perfil', label: 'Perfil', path: '/perfil' },
  { key: 'instituciones', label: 'Instituciones', path: '/instituciones' },
  { key: 'campus', label: 'Campus', path: '/complejos' },
  { key: 'torres', label: 'Torres', path: '/torres' },
  { key: 'pisos', label: 'Pisos', path: '/pisos' },
  { key: 'salas-espera', label: 'Salas de espera', path: '/salas-espera' },
  { key: 'clusters-turnos', label: 'Clústers', path: '/clusters-turnos' },
  { key: 'consultorios', label: 'Consultorios', path: '/consultorios' },
  { key: 'consulta-clusters-consultorios', label: 'Consulta de clústers', path: '/consulta-clusters-consultorios' },
  { key: 'usuarios', label: 'Usuarios', path: '/usuarios' },
  { key: 'busqueda-usuarios', label: 'Búsqueda de usuarios', path: '/busqueda-usuarios' },
  { key: 'roles', label: 'Roles', path: '/roles' },
  { key: 'usuario-roles', label: 'Asignación de usuarios', path: '/usuario-roles' },
  { key: 'medicos', label: 'Médicos', path: '/medicos' },
  { key: 'operadores', label: 'Operadores', path: '/operadores' },
  { key: 'pacientes', label: 'Pacientes', path: '/pacientes' },
  { key: 'citas', label: 'Citas', path: '/citas' },
  { key: 'citas-hoy', label: 'Citas de hoy', path: '/citas/hoy' },
  { key: 'contactos-institucionales', label: 'Contactos institucionales', path: '/contactos-institucionales' },
  { key: 'asignaciones', label: 'Asignaciones', path: '/asignaciones' },
  { key: 'pantallas-turnos', label: 'Pantallas de turnos', path: '/pantallas-turnos' },
  { key: 'kioskos', label: 'Kioskos', path: '/kioskos' },
  { key: 'turnos-llamados', label: 'Turnos llamados', path: '/turnos-llamados' },
  { key: 'reportes', label: 'Reportes', path: '/reportes' },
  { key: 'auditoria', label: 'Auditoría', path: '/auditoria' },
];

export const screenByPath = new Map(screens.map((screen) => [screen.path, screen]));

export function accessForPath(user: Usuario | null, path: string): AccessLevel {
  if (!user?.permisos) return 'editar';
  const screen = screenByPath.get(path);
  if (!screen) return 'editar';
  return user.permisos[screen.key] ?? 'sin';
}

export function canAccessPath(user: Usuario | null, path: string) {
  return accessForPath(user, path) !== 'sin';
}
