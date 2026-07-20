<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';

type Mode = 'home' | 'search' | 'scan' | 'result';

type CitaSearchResult = {
  id: string;
  folio_turno: string;
  hora_cita: string;
  consultorio?: string | null;
  piso?: string | null;
  estado: string;
};

type CheckinResponse = {
  resultado: string;
  mensaje: string;
  folio_turno?: string | null;
  estado_cita?: string | null;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';
const urlParams = new URLSearchParams(window.location.search);
const dispositivoId = urlParams.get('device') || 'kiosk-web';
const mode = ref<Mode>('home');
const status = ref('');
const apiStatus = ref('Verificando API...');
const version = import.meta.env.VITE_APP_VERSION ?? 'v0.2.0';
const nombreApellido = ref('');
const celular = ref('');
const fechaNacimiento = ref('');
const qrToken = ref('');
const citas = ref<CitaSearchResult[]>([]);
const result = ref<CheckinResponse | null>(null);
const error = ref('');
const loading = ref(false);
const currentDateTime = ref('');
let clockTimer: number | undefined;

function todayLocalIso() {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

function updateClock() {
  currentDateTime.value = new Intl.DateTimeFormat('es-MX', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date());
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
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

function openMode(next: Mode) {
  mode.value = next;
  status.value = '';
  error.value = '';
  result.value = null;
}

function backHome() {
  mode.value = 'home';
  status.value = 'Seleccione una acción para continuar.';
  error.value = '';
  result.value = null;
}

async function searchCitas() {
  if (!nombreApellido.value.trim()) {
    error.value = 'Capture nombre y apellido.';
    return;
  }
  loading.value = true;
  error.value = '';
  try {
    const query = new URLSearchParams({
      paciente: nombreApellido.value.trim(),
      fecha: todayLocalIso(),
    });
    if (celular.value.trim()) query.set('celular', celular.value.trim());
    if (fechaNacimiento.value) query.set('fecha_nacimiento', fechaNacimiento.value);
    citas.value = await apiFetch<CitaSearchResult[]>(`/citas/buscar?${query.toString()}`);
    status.value = citas.value.length === 1 ? 'Una cita encontrada.' : `${citas.value.length} citas encontradas para hoy.`;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible buscar citas.';
  } finally {
    loading.value = false;
  }
}

async function checkinCita(citaId: string) {
  loading.value = true;
  error.value = '';
  try {
    result.value = await apiFetch<CheckinResponse>(`/citas/${citaId}/checkin-lobby`, {
      method: 'POST',
      body: JSON.stringify({ canal: 'KIOSKO', dispositivo_id: dispositivoId }),
    });
    mode.value = 'result';
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible registrar la llegada.';
  } finally {
    loading.value = false;
  }
}

async function checkinQr() {
  if (!qrToken.value.trim()) return;
  loading.value = true;
  error.value = '';
  try {
    result.value = await apiFetch<CheckinResponse>('/qr/checkin', {
      method: 'POST',
      body: JSON.stringify({ token: qrToken.value.trim(), canal: 'KIOSKO', dispositivo_id: dispositivoId }),
    });
    mode.value = 'result';
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible validar el QR.';
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  updateClock();
  clockTimer = window.setInterval(updateClock, 1000);
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    const data = await response.json();
    apiStatus.value = data.status === 'ok' ? 'API OK' : 'API no disponible';
  } catch {
    apiStatus.value = 'API no disponible';
  }
});

onBeforeUnmount(() => {
  if (clockTimer !== undefined) {
    window.clearInterval(clockTimer);
  }
});
</script>

<template>
  <main class="kiosk-shell">
    <div class="kiosk-clock">{{ currentDateTime }}</div>
    <section class="kiosk-stage">
      <div>
        <h1>Bienvenido</h1>
        <p>Registro de llegada para citas de hoy.</p>
      </div>
      <div class="system-status">
        <span>{{ apiStatus }}</span>
        <span>{{ version }}</span>
      </div>

      <div v-if="mode === 'home'" class="actions">
        <button class="primary" type="button" @click="openMode('scan')">Escanear QR</button>
        <button class="secondary" type="button" @click="openMode('search')">Buscar cita</button>
      </div>

      <form v-else-if="mode === 'search'" class="kiosk-card" @submit.prevent="searchCitas">
        <label for="search-name">Nombre y apellido</label>
        <input id="search-name" v-model="nombreApellido" autocomplete="name" autofocus required />
        <label for="search-phone">Celular (opcional)</label>
        <input id="search-phone" v-model="celular" autocomplete="tel" inputmode="tel" />
        <label for="search-birthdate">Fecha de nacimiento (opcional)</label>
        <input id="search-birthdate" v-model="fechaNacimiento" type="date" />
        <button class="primary" type="submit" :disabled="loading">Buscar</button>
        <button class="secondary" type="button" @click="backHome">Volver</button>
        <div v-if="citas.length" class="result-list">
          <button v-for="cita in citas" :key="cita.id" class="result-item" type="button" @click="checkinCita(cita.id)">
            <strong>{{ cita.folio_turno }}</strong>
            <span>{{ cita.hora_cita.slice(0, 5) }} · {{ cita.consultorio || 'Consultorio' }} · {{ cita.piso || 'Piso' }}</span>
          </button>
        </div>
      </form>

      <form v-else-if="mode === 'scan'" class="kiosk-card" @submit.prevent="checkinQr">
        <div class="scan-box">Cámara pendiente</div>
        <label for="qr">Token QR</label>
        <input id="qr" v-model="qrToken" autocomplete="off" placeholder="Pegar token temporalmente" />
        <button class="primary" type="submit" :disabled="loading">Validar QR</button>
        <button class="secondary" type="button" @click="backHome">Volver</button>
      </form>

      <div v-else class="kiosk-card result-card" :class="result?.resultado?.toLowerCase()">
        <strong>{{ result?.resultado }}</strong>
        <p>{{ result?.mensaje }}</p>
        <p v-if="result?.folio_turno">Turno {{ result.folio_turno }}</p>
        <button class="secondary" type="button" @click="backHome">Finalizar</button>
      </div>

      <div class="notice" aria-live="polite">{{ error || status || 'Seleccione una acción para continuar.' }}</div>
    </section>
  </main>
</template>
