<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

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

type KioskoConfig = {
  codigo_dispositivo: string;
  nombre?: string | null;
  polling_interval_seconds: number;
  color_fondo?: string | null;
  color_texto?: string | null;
  color_primario?: string | null;
  color_acento?: string | null;
};

type PacienteOption = {
  id: string;
  label: string;
  homonimo: boolean;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';
const urlParams = new URLSearchParams(window.location.search);
const dispositivoId = urlParams.get('device') || 'kiosk-web';
const kioskToken = urlParams.get('token') || '';
const mode = ref<Mode>('home');
const status = ref('');
const apiStatus = ref('Verificando API...');
const version = import.meta.env.VITE_APP_VERSION ?? 'v0.2.0';
const kioskoConfig = ref<KioskoConfig | null>(null);
const nombreApellido = ref('');
const pacienteOptions = ref<PacienteOption[]>([]);
const selectedPaciente = ref<PacienteOption | null>(null);
const showPacienteOptions = ref(false);
const celular = ref('');
const fechaNacimiento = ref('');
const qrToken = ref('');
const citas = ref<CitaSearchResult[]>([]);
const result = ref<CheckinResponse | null>(null);
const error = ref('');
const loading = ref(false);
const currentDateTime = ref('');
let clockTimer: number | undefined;
let pacienteSearchRequest = 0;

const kioskoNombre = computed(() => kioskoConfig.value?.nombre?.trim() || kioskoConfig.value?.codigo_dispositivo || dispositivoId);

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

function removeAccents(value: string) {
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

function patientLookupLetterCount(value: string) {
  return (removeAccents(value).match(/[A-Za-z]/g) ?? []).length;
}

function clearSearchFields() {
  pacienteSearchRequest += 1;
  nombreApellido.value = '';
  selectedPaciente.value = null;
  pacienteOptions.value = [];
  showPacienteOptions.value = false;
  celular.value = '';
  fechaNacimiento.value = '';
  citas.value = [];
  status.value = '';
  error.value = '';
}

async function loadPacienteOptions() {
  const queryText = nombreApellido.value.trim();
  const requestId = ++pacienteSearchRequest;
  if (patientLookupLetterCount(queryText) < 4) {
    pacienteOptions.value = [];
    showPacienteOptions.value = false;
    return;
  }
  try {
    const query = new URLSearchParams({ q: queryText });
    if (kioskToken) query.set('token', kioskToken);
    const options = await apiFetch<PacienteOption[]>(
      `/kioskos/public/${encodeURIComponent(dispositivoId)}/pacientes/buscar?${query.toString()}`,
    );
    if (requestId !== pacienteSearchRequest) return;
    pacienteOptions.value = options;
    showPacienteOptions.value = options.length > 0;
  } catch (err) {
    if (requestId !== pacienteSearchRequest) return;
    pacienteOptions.value = [];
    showPacienteOptions.value = false;
    error.value = err instanceof Error ? err.message : 'No fue posible buscar pacientes.';
  }
}

function onPacienteInput() {
  if (selectedPaciente.value && nombreApellido.value !== selectedPaciente.value.label) {
    selectedPaciente.value = null;
  }
  citas.value = [];
  if (patientLookupLetterCount(nombreApellido.value) < 4) {
    pacienteSearchRequest += 1;
    pacienteOptions.value = [];
    showPacienteOptions.value = false;
    return;
  }
  void loadPacienteOptions();
}

function onPacienteFocus() {
  if (pacienteOptions.value.length) {
    showPacienteOptions.value = true;
    return;
  }
  void loadPacienteOptions();
}

function hidePacienteOptionsSoon() {
  window.setTimeout(() => {
    showPacienteOptions.value = false;
  }, 150);
}

function selectPaciente(option: PacienteOption) {
  selectedPaciente.value = option;
  nombreApellido.value = option.label;
  pacienteOptions.value = [];
  showPacienteOptions.value = false;
  error.value = '';
  status.value = option.homonimo ? 'Capture celular o fecha de nacimiento para confirmar al paciente.' : 'Paciente seleccionado.';
}

function openMode(next: Mode) {
  mode.value = next;
  status.value = '';
  error.value = '';
  result.value = null;
  if (next === 'search') {
    clearSearchFields();
  }
  if (next === 'scan') {
    qrToken.value = '';
  }
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
  if (selectedPaciente.value?.homonimo && !celular.value.trim() && !fechaNacimiento.value) {
    error.value = 'Capture celular o fecha de nacimiento para confirmar al paciente.';
    return;
  }
  loading.value = true;
  error.value = '';
  try {
    const query = new URLSearchParams({
      paciente: nombreApellido.value.trim(),
    });
    if (selectedPaciente.value) query.set('paciente_id', selectedPaciente.value.id);
    if (celular.value.trim()) query.set('celular', celular.value.trim());
    if (fechaNacimiento.value) query.set('fecha_nacimiento', fechaNacimiento.value);
    if (kioskToken) query.set('token', kioskToken);
    citas.value = await apiFetch<CitaSearchResult[]>(
      `/kioskos/public/${encodeURIComponent(dispositivoId)}/citas/buscar?${query.toString()}`,
    );
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
    result.value = await apiFetch<CheckinResponse>(`/kioskos/public/${encodeURIComponent(dispositivoId)}/citas/${citaId}/checkin-lobby`, {
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
    result.value = await apiFetch<CheckinResponse>(`/kioskos/public/${encodeURIComponent(dispositivoId)}/qr/checkin`, {
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

async function loadKioskoConfig() {
  const query = new URLSearchParams();
  if (kioskToken) query.set('token', kioskToken);
  const suffix = query.toString() ? `?${query.toString()}` : '';
  try {
    kioskoConfig.value = await apiFetch<KioskoConfig>(`/kioskos/public/${encodeURIComponent(dispositivoId)}/config${suffix}`);
  } catch (err) {
    status.value = err instanceof Error ? err.message : 'No fue posible cargar el kiosko.';
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
  await loadKioskoConfig();
});

onBeforeUnmount(() => {
  if (clockTimer !== undefined) {
    window.clearInterval(clockTimer);
  }
});
</script>

<template>
  <main class="kiosk-shell">
    <div class="kiosk-name">{{ kioskoNombre }}</div>
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
        <div class="patient-search">
          <input
            id="search-name"
            v-model="nombreApellido"
            autocomplete="name"
            autofocus
            required
            @blur="hidePacienteOptionsSoon"
            @focus="onPacienteFocus"
            @input="onPacienteInput"
          />
          <div v-if="showPacienteOptions" class="patient-options">
            <button
              v-for="option in pacienteOptions"
              :key="option.id"
              class="patient-option"
              type="button"
              @mousedown.prevent="selectPaciente(option)"
            >
              <span>{{ option.label }}</span>
              <small v-if="option.homonimo">Requiere celular o fecha de nacimiento</small>
            </button>
          </div>
        </div>
        <label for="search-phone">Celular (opcional)</label>
        <input id="search-phone" v-model="celular" autocomplete="tel" inputmode="tel" />
        <label for="search-birthdate">Fecha de nacimiento (opcional)</label>
        <input id="search-birthdate" v-model="fechaNacimiento" type="date" />
        <div class="search-actions">
          <button class="primary" type="submit" :disabled="loading">Buscar</button>
          <button class="secondary" type="button" @click="clearSearchFields">Limpiar</button>
          <button class="secondary" type="button" @click="backHome">Volver</button>
        </div>
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
