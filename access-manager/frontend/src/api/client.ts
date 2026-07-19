const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';
const TOKEN_KEY = 'access_manager_token';

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(message: string, status: number, detail: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

function errorMessage(detail: unknown, fallback = 'Error de API') {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (!item || typeof item !== 'object') return '';
        const loc =
          'loc' in item && Array.isArray(item.loc) ? (item.loc as unknown[]).filter((part) => part !== 'body').join('.') : '';
        const rawMsg = 'msg' in item && typeof item.msg === 'string' ? item.msg : fallback;
        const msg = rawMsg.replace(/^Value error,\s*/, '');
        const ctx = 'ctx' in item && item.ctx && typeof item.ctx === 'object' ? item.ctx : {};
        if ('type' in item && item.type === 'string_too_short' && 'min_length' in ctx) {
          return `${loc}: debe tener al menos ${String(ctx.min_length)} caracteres`;
        }
        if ('type' in item && item.type === 'missing') {
          return `${loc}: campo requerido`;
        }
        return loc ? `${loc}: ${msg}` : msg;
      })
      .filter(Boolean);
    return messages.length ? messages.join(' · ') : fallback;
  }
  if (detail && typeof detail === 'object' && 'mensaje' in detail && typeof detail.mensaje === 'string') {
    return detail.mensaje;
  }
  if (detail && typeof detail === 'object' && 'detail' in detail) {
    return errorMessage((detail as { detail: unknown }).detail, fallback);
  }
  return fallback;
}

export type ApiHealth = {
  status: string;
  service?: string;
  version?: string;
};

export type Institucion = {
  id: string;
  nombre: string;
  razon_social?: string | null;
  notas?: string | null;
  logo_url?: string | null;
  color_primario?: string | null;
  color_secundario?: string | null;
  color_acento?: string | null;
  activo: boolean;
  created_at: string;
  updated_at: string;
};

export type Complejo = {
  id: string;
  institucion_id: string;
  nombre: string;
  descripcion?: string | null;
  logo_url?: string | null;
  direccion?: string | null;
  telefono?: string | null;
  zona_horaria: string;
  color_primario?: string | null;
  color_secundario?: string | null;
  color_acento?: string | null;
  activo: boolean;
  created_at: string;
  updated_at: string;
};

export type Usuario = {
  id: string;
  nombre: string;
  email: string;
  telefono?: string | null;
  two_factor_enabled: boolean;
  force_password_change: boolean;
  estado: string;
  created_at: string;
  updated_at: string;
};

export type Role = {
  id: string;
  codigo: string;
  nombre: string;
  descripcion?: string | null;
  activo: boolean;
  created_at: string;
  updated_at: string;
};

export type UsuarioRol = {
  id: string;
  usuario_id: string;
  rol_id: string;
  institucion_id?: string | null;
  complejo_id?: string | null;
  activo: boolean;
  created_at: string;
  updated_at: string;
};

export type Piso = {
  id: string;
  complejo_id: string;
  numero: string;
  nombre_visible: string;
  descripcion?: string | null;
  activo: boolean;
  created_at: string;
  updated_at: string;
};

export type SalaEspera = {
  id: string;
  complejo_id: string;
  piso_id: string;
  nombre: string;
  descripcion?: string | null;
  capacidad_estimada?: number | null;
  activa: boolean;
  created_at: string;
  updated_at: string;
};

export type Consultorio = {
  id: string;
  complejo_id: string;
  piso_id: string;
  codigo: string;
  nombre_visible?: string | null;
  instrucciones_acceso?: string | null;
  cluster_ids: string[];
  activo: boolean;
  created_at: string;
  updated_at: string;
};

export type ClusterTurnos = {
  id: string;
  complejo_id: string;
  piso_id: string;
  nombre: string;
  descripcion?: string | null;
  activo: boolean;
  created_at: string;
  updated_at: string;
};

export type Medico = {
  id: string;
  usuario_id?: string | null;
  nombre: string;
  apellidos: string;
  nombre_visible?: string | null;
  plantilla_turno: string;
  activo: boolean;
  created_at: string;
  updated_at: string;
};

export type Operador = {
  id: string;
  usuario_id: string;
  activo: boolean;
  created_at: string;
  updated_at: string;
};

export type PuntoAcceso = {
  id: string;
  complejo_id: string;
  piso_id: string;
  nombre: string;
  descripcion?: string | null;
  activo: boolean;
  created_at: string;
  updated_at: string;
};

export type Kiosko = {
  id: string;
  codigo_dispositivo: string;
  complejo_id: string;
  piso_id: string;
  punto_acceso_id: string;
  nombre?: string | null;
  descripcion?: string | null;
  activo: boolean;
  ultima_conexion?: string | null;
  polling_interval_seconds: number;
  color_fondo?: string | null;
  color_texto?: string | null;
  color_primario?: string | null;
  color_acento?: string | null;
  created_at: string;
  updated_at: string;
};

export type AsignacionMedicoConsultorio = {
  id: string;
  medico_id: string;
  consultorio_id: string;
  fecha_inicio: string;
  fecha_fin?: string | null;
  hora_inicio?: string | null;
  hora_fin?: string | null;
  dias_semana?: string | null;
  activo: boolean;
  created_at: string;
  updated_at: string;
};

export type AsignacionOperador = {
  id: string;
  operador_id: string;
  medico_id?: string | null;
  consultorio_id?: string | null;
  complejo_id: string;
  fecha_inicio: string;
  fecha_fin?: string | null;
  prioridad: number;
  activo: boolean;
  created_at: string;
  updated_at: string;
};

export type PantallaTurnos = {
  id: string;
  codigo_dispositivo: string;
  complejo_id: string;
  piso_id?: string | null;
  cluster_espera_id?: string | null;
  cluster_ids: string[];
  consultorio_id?: string | null;
  nombre?: string | null;
  descripcion?: string | null;
  activa: boolean;
  ultima_conexion?: string | null;
  polling_interval_seconds: number;
  color_fondo?: string | null;
  color_texto?: string | null;
  color_turno_nuevo?: string | null;
  color_turno_normal?: string | null;
  font_size_turno_nuevo?: number | null;
  font_size_turno_normal?: number | null;
  segundos_resaltado: number;
  segundos_visible: number;
  max_turnos_visibles: number;
  created_at: string;
  updated_at: string;
};

export type PublicDisplayConfig = {
  polling_interval_seconds: number;
  color_fondo?: string | null;
  color_texto?: string | null;
  color_turno_nuevo?: string | null;
  color_turno_normal?: string | null;
  font_size_turno_nuevo?: number | null;
  font_size_turno_normal?: number | null;
  segundos_resaltado: number;
  segundos_visible: number;
  max_turnos_visibles: number;
};

export type PublicDisplayTurno = {
  turno: string;
  consultorio: string;
  texto?: string | null;
  estado: string;
  llamado_en: string;
  resaltado: boolean;
};

export type PublicDisplayResponse = {
  codigo_dispositivo: string;
  ultima_conexion: string;
  config: PublicDisplayConfig;
  turnos: PublicDisplayTurno[];
};

export type TurnoDisplayReciente = {
  cita_id?: string | null;
  turno: string;
  consultorio: string;
  texto?: string | null;
  llamado_en: string;
  estado: string;
  estado_cita?: string | null;
  llamado_numero: number;
};

export type Paciente = {
  id: string;
  folio_paciente: string;
  nombre?: string | null;
  nombre_preferido?: string | null;
  apellido_paterno?: string | null;
  apellido_materno?: string | null;
  celular?: string | null;
  fecha_nacimiento?: string | null;
  activo: boolean;
  desactivado_en?: string | null;
  marcado_borrado_en?: string | null;
  created_at: string;
  updated_at: string;
};

export type MedioContacto = {
  tipo: 'CELULAR' | 'CORREO';
  valor: string;
};

export type ContactoInstitucional = {
  id: string;
  nombre: string;
  medios_contacto: MedioContacto[];
  tipo_contacto: 'PRIMARIO' | 'SECUNDARIO' | 'SOLO_EMERGENCIAS' | 'OTRO';
  tipo_contacto_descripcion?: string | null;
  notas?: string | null;
  complejo_ids: string[];
  created_at: string;
  updated_at: string;
};

export type Cita = {
  id: string;
  tipo: string;
  estado: string;
  paciente_id: string;
  medico_id: string;
  consultorio_id: string;
  complejo_id: string;
  piso_id: string;
  sala_prevista_id?: string | null;
  fecha_cita: string;
  hora_cita: string;
  duracion_estimada?: number | null;
  folio_turno: string;
  origen?: string | null;
  notas_operativas?: string | null;
  creada_por?: string | null;
  created_at: string;
  updated_at: string;
  paciente?: string | null;
  paciente_nombre_completo?: string | null;
  consultorio?: string | null;
  piso?: string | null;
  medico?: string | null;
};

export type CitaSearchResult = {
  id: string;
  folio_turno: string;
  hora_cita: string;
  consultorio?: string | null;
  piso?: string | null;
  estado: string;
};

export type QrGenerateResponse = {
  id: string;
  cita_id: string;
  estado: string;
  fecha_emision: string;
  fecha_expiracion: string;
  qr_payload: string;
};

export type TicketResponse = {
  encabezado_fecha: string;
  leyenda: string;
  turno: string;
  qr_payload: string;
  consultorio: string;
  piso: string;
  hora: string;
};

export type CheckinResponse = {
  resultado: string;
  mensaje: string;
  cita_id?: string | null;
  folio_turno?: string | null;
  estado_cita?: string | null;
};

export type Auditoria = {
  id: string;
  evento: string;
  entidad: string;
  entidad_id?: string | null;
  usuario_id?: string | null;
  canal?: string | null;
  ip_origen?: string | null;
  valor_antes?: Record<string, unknown> | null;
  valor_despues?: Record<string, unknown> | null;
  created_at: string;
};

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Error de API' }));
    const detail = error.detail ?? error;
    throw new ApiError(errorMessage(detail), response.status, detail);
  }

  return response.json() as Promise<T>;
}

export async function apiFetchPublic<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Error de API' }));
    const detail = error.detail ?? error;
    throw new ApiError(errorMessage(detail), response.status, detail);
  }

  return response.json() as Promise<T>;
}

export async function login(email: string, password: string) {
  return apiFetch<{ access_token: string; token_type: string }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export function getCurrentUser() {
  return apiFetch<Usuario>('/auth/me');
}

export function changeMyPassword(payload: { current_password: string; new_password: string }) {
  return apiFetch<Usuario>('/auth/password', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getApiHealth() {
  return apiFetch<ApiHealth>('/health');
}

export function listResource<T>(resource: string) {
  return apiFetch<T[]>(`/${resource}`);
}

export function createResource<T>(resource: string, payload: Record<string, unknown>) {
  return apiFetch<T>(`/${resource}`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateResource<T>(resource: string, id: string, payload: Record<string, unknown>) {
  return apiFetch<T>(`/${resource}/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function activateResource<T>(resource: string, id: string) {
  return apiFetch<T>(`/${resource}/${id}/activar`, {
    method: 'POST',
  });
}

export function deactivateResource<T>(resource: string, id: string) {
  return apiFetch<T>(`/${resource}/${id}/desactivar`, {
    method: 'POST',
  });
}

export function listInstituciones(q?: string) {
  const query = q ? `?q=${encodeURIComponent(q)}` : '';
  return apiFetch<Institucion[]>(`/instituciones${query}`);
}

export function createInstitucion(payload: Pick<Institucion, 'nombre'> & Partial<Institucion>) {
  return apiFetch<Institucion>('/instituciones', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateInstitucion(id: string, payload: Partial<Institucion>) {
  return apiFetch<Institucion>(`/instituciones/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function activateInstitucion(id: string) {
  return apiFetch<Institucion>(`/instituciones/${id}/activar`, { method: 'POST' });
}

export function deactivateInstitucion(id: string) {
  return apiFetch<Institucion>(`/instituciones/${id}/desactivar`, { method: 'POST' });
}

export function listComplejos() {
  return apiFetch<Complejo[]>('/complejos');
}

export function listZonasHorarias() {
  return apiFetch<string[]>('/complejos/zonas-horarias');
}

export function createComplejo(payload: {
  institucion_id: string;
  nombre: string;
  descripcion?: string;
  direccion?: string;
  telefono?: string;
  zona_horaria: string;
  activo?: boolean;
}) {
  return apiFetch<Complejo>('/complejos', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateComplejo(id: string, payload: Partial<Complejo>) {
  return apiFetch<Complejo>(`/complejos/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function activateComplejo(id: string) {
  return apiFetch<Complejo>(`/complejos/${id}/activar`, { method: 'POST' });
}

export function deactivateComplejo(id: string) {
  return apiFetch<Complejo>(`/complejos/${id}/desactivar`, { method: 'POST' });
}

export const listUsuarios = () => listResource<Usuario>('usuarios');
export const listRoles = () => listResource<Role>('roles');
export const listUsuarioRoles = () => listResource<UsuarioRol>('usuario-roles');
export const listPisos = () => listResource<Piso>('pisos');
export const listSalasEspera = () => listResource<SalaEspera>('salas-espera');
export const listClustersTurnos = () => listResource<ClusterTurnos>('clusters-turnos');
export const listConsultorios = () => listResource<Consultorio>('consultorios');
export const listMedicos = () => listResource<Medico>('medicos');
export const listOperadores = () => listResource<Operador>('operadores');
export const listPuntosAcceso = () => listResource<PuntoAcceso>('puntos-acceso');
export const listKioskos = () => listResource<Kiosko>('kioskos');
export const listPantallasTurnos = () => listResource<PantallaTurnos>('pantallas-turnos');
export const listContactosInstitucionales = () => listResource<ContactoInstitucional>('contactos-institucionales');
export const listAsignacionesMedicoConsultorio = () =>
  listResource<AsignacionMedicoConsultorio>('asignaciones-medico-consultorio');
export const listAsignacionesOperador = () =>
  listResource<AsignacionOperador>('asignaciones-operador');
export const listAuditoria = () => listResource<Auditoria>('auditoria');
export const listPacientes = () => listResource<Paciente>('pacientes');

export type CitaFilters = {
  fecha?: string;
  complejo_id?: string;
  piso_id?: string;
  consultorio_id?: string;
  medico_id?: string;
  paciente?: string;
  estado?: string;
  tipo?: string;
};

function queryString(params: Record<string, string | number | boolean | null | undefined>) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      query.set(key, String(value));
    }
  }
  const text = query.toString();
  return text ? `?${text}` : '';
}

export const listCitas = (params: CitaFilters = {}) => apiFetch<Cita[]>(`/citas${queryString(params)}`);
export const listCitasHoy = (params: CitaFilters = {}) => apiFetch<Cita[]>(`/citas/hoy${queryString(params)}`);

export function searchPacientes(q: string) {
  return apiFetch<Paciente[]>(`/pacientes/buscar?q=${encodeURIComponent(q)}`);
}

export function createPaciente(payload: Partial<Paciente>) {
  return apiFetch<Paciente>('/pacientes', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updatePaciente(id: string, payload: Partial<Paciente>) {
  return apiFetch<Paciente>(`/pacientes/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function activatePaciente(id: string) {
  return apiFetch<Paciente>(`/pacientes/${id}/activar`, { method: 'PATCH' });
}

export function deactivatePaciente(id: string) {
  return apiFetch<Paciente>(`/pacientes/${id}/desactivar`, { method: 'PATCH' });
}

export function markPacienteForDeletion(id: string) {
  return apiFetch<Paciente>(`/pacientes/${id}/marcar-borrado`, { method: 'PATCH' });
}

export function createContactoInstitucional(payload: Record<string, unknown>) {
  return apiFetch<ContactoInstitucional>('/contactos-institucionales', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateContactoInstitucional(id: string, payload: Record<string, unknown>) {
  return apiFetch<ContactoInstitucional>(`/contactos-institucionales/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function createPantallaTurnos(payload: Record<string, unknown>) {
  return apiFetch<PantallaTurnos>('/pantallas-turnos', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updatePantallaTurnos(id: string, payload: Record<string, unknown>) {
  return apiFetch<PantallaTurnos>(`/pantallas-turnos/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function activatePantallaTurnos(id: string) {
  return apiFetch<PantallaTurnos>(`/pantallas-turnos/${id}/activar`, { method: 'POST' });
}

export function deactivatePantallaTurnos(id: string) {
  return apiFetch<PantallaTurnos>(`/pantallas-turnos/${id}/desactivar`, { method: 'POST' });
}

export function createPuntoAcceso(payload: Record<string, unknown>) {
  return apiFetch<PuntoAcceso>('/puntos-acceso', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updatePuntoAcceso(id: string, payload: Record<string, unknown>) {
  return apiFetch<PuntoAcceso>(`/puntos-acceso/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function activatePuntoAcceso(id: string) {
  return apiFetch<PuntoAcceso>(`/puntos-acceso/${id}/activar`, { method: 'POST' });
}

export function deactivatePuntoAcceso(id: string) {
  return apiFetch<PuntoAcceso>(`/puntos-acceso/${id}/desactivar`, { method: 'POST' });
}

export function createKiosko(payload: Record<string, unknown>) {
  return apiFetch<Kiosko>('/kioskos', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateKiosko(id: string, payload: Record<string, unknown>) {
  return apiFetch<Kiosko>(`/kioskos/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function activateKiosko(id: string) {
  return apiFetch<Kiosko>(`/kioskos/${id}/activar`, { method: 'POST' });
}

export function deactivateKiosko(id: string) {
  return apiFetch<Kiosko>(`/kioskos/${id}/desactivar`, { method: 'POST' });
}

export function searchCitas(params: {
  paciente: string;
  fecha?: string;
  complejo_id?: string;
  piso_id?: string;
  consultorio_id?: string;
  medico_id?: string;
  celular?: string;
  fecha_nacimiento?: string;
  estado?: string;
  tipo?: string;
}) {
  return apiFetchPublic<CitaSearchResult[]>(`/citas/buscar${queryString(params)}`);
}

export function createCita(payload: Record<string, unknown>, confirmarDuplicado = false) {
  const query = confirmarDuplicado ? '?confirmar_duplicado=true' : '';
  return apiFetch<Cita>(`/citas${query}`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateCita(id: string, payload: Record<string, unknown>, confirmarDuplicado = false) {
  const query = confirmarDuplicado ? '?confirmar_duplicado=true' : '';
  return apiFetch<Cita>(`/citas/${id}${query}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function generarQr(citaId: string) {
  return apiFetch<QrGenerateResponse>(`/citas/${citaId}/qr`, { method: 'POST' });
}

export function getTicket(citaId: string) {
  return apiFetch<TicketResponse>(`/citas/${citaId}/ticket`);
}

export function checkinLobby(citaId: string, canal = 'RECEPCION') {
  return apiFetchPublic<CheckinResponse>(`/citas/${citaId}/checkin-lobby`, {
    method: 'POST',
    body: JSON.stringify({ canal }),
  });
}

export function qrCheckin(token: string, canal = 'KIOSKO') {
  return apiFetchPublic<CheckinResponse>('/qr/checkin', {
    method: 'POST',
    body: JSON.stringify({ token, canal }),
  });
}

export function validarQr(token: string) {
  return apiFetchPublic<CheckinResponse>('/qr/validar', {
    method: 'POST',
    body: JSON.stringify({ token }),
  });
}

export function cancelarCita(citaId: string) {
  return apiFetch<{ id: string; estado: string; folio_turno: string }>(`/citas/${citaId}/cancelar`, { method: 'PATCH' });
}

export function autorizarPasar(citaId: string) {
  return apiFetch<{ id: string; estado: string; folio_turno: string }>(`/citas/${citaId}/autorizar-pasar`, { method: 'PATCH' });
}

export function llamarCita(citaId: string) {
  return apiFetch<{
    id: string;
    turno: string;
    consultorio: string;
    texto?: string | null;
    estado: string;
    estado_cita: string;
    llamado_numero: number;
  }>(`/citas/${citaId}/llamar`, { method: 'POST' });
}

export function auditCitasExport(params: CitaFilters & { formato: 'excel' | 'csv' | 'json' }) {
  return apiFetch<{ ok: boolean }>(`/citas/exportacion${queryString(params)}`, { method: 'POST' });
}

export function getPublicDisplayTurnos(codigoDispositivo: string, token?: string) {
  const params = new URLSearchParams();
  if (token) {
    params.set('token', token);
  }
  const query = params.toString();
  return apiFetchPublic<PublicDisplayResponse>(
    `/public-display/${encodeURIComponent(codigoDispositivo)}/turnos${query ? `?${query}` : ''}`,
  );
}

export function listTurnosDisplayRecientes(params: {
  complejo_id: string;
  piso_id?: string;
  cluster_espera_id?: string;
  consultorio_id?: string;
  minutos?: number;
}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') {
      query.set(key, String(value));
    }
  }
  return apiFetch<TurnoDisplayReciente[]>(`/turnos-display/recientes?${query.toString()}`);
}
