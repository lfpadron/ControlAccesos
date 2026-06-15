export type CitaSearchResult = {
  id: string;
  folio_turno: string;
  hora_cita: string;
  consultorio?: string | null;
  piso?: string | null;
  estado: string;
};

export type CheckinResponse = {
  resultado: string;
  mensaje: string;
  cita_id?: string | null;
  folio_turno?: string | null;
  estado_cita?: string | null;
};

export async function apiFetch<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: 'Error de API' }));
    const detail = typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail ?? payload);
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export function searchCitas(paciente: string) {
  return apiFetch<CitaSearchResult[]>(`/citas/buscar?paciente=${encodeURIComponent(paciente)}`);
}

export function checkinLobby(citaId: string, canal = 'APP_MOVIL') {
  return apiFetch<CheckinResponse>(`/citas/${citaId}/checkin-lobby`, {
    method: 'POST',
    body: JSON.stringify({ canal, dispositivo_id: 'mobile-pwa' }),
  });
}

export function checkinQr(token: string) {
  return apiFetch<CheckinResponse>('/qr/checkin', {
    method: 'POST',
    body: JSON.stringify({ token, canal: 'APP_MOVIL', dispositivo_id: 'mobile-pwa' }),
  });
}
