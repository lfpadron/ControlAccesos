<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import QRCode from 'qrcode';
import { getPublicDisplayTurnos, PublicDisplayConfig, PublicDisplayProximaCita, PublicDisplayTurno } from '../api/client';

const VOICE_SETTING_KEY = 'access_manager_display_voice_enabled';
type DisplayMode = 'turnos' | 'proxima_cita';

const route = useRoute();
const codigoDispositivo = computed(() => String(route.params.codigo_dispositivo ?? ''));
const token = computed(() => (typeof route.query.token === 'string' ? route.query.token : undefined));
const turnos = ref<PublicDisplayTurno[]>([]);
const allProximasCitas = ref<PublicDisplayProximaCita[]>([]);
const proximaCitaPage = ref(0);
const displayMode = ref<DisplayMode>('turnos');
const config = ref<PublicDisplayConfig>({
  polling_interval_seconds: 5,
  segundos_resaltado: 25,
  segundos_visible: 300,
  max_turnos_visibles: 10,
  mostrar_turnos: true,
  mostrar_proxima_cita: false,
  max_citas_proximas: 10,
});
const connected = ref(false);
const lastUpdate = ref('');
const currentTime = ref('');
const error = ref('');
const displayQr = ref('');
const displayName = ref('');
const voiceSupported = ref(false);
const voiceEnabled = ref(false);
let timer: number | undefined;
let turnoTimingTimer: number | undefined;
let clockTimer: number | undefined;
let knownTurnoKeys = new Set<string>();
let hasLoadedTurnos = false;
let serverClockOffsetMs = 0;

const screenStyle = computed(() => ({
  '--display-bg': config.value.color_fondo || '#06111f',
  '--display-text': config.value.color_texto || '#f8fbff',
  '--display-new': config.value.color_turno_nuevo || '#34d399',
  '--display-normal': config.value.color_turno_normal || '#f8fbff',
  '--display-new-size': `${config.value.font_size_turno_nuevo || 96}px`,
  '--display-normal-size': `${config.value.font_size_turno_normal || 64}px`,
}));
const hasHighlightedTurnos = computed(() => turnos.value.some((item) => item.resaltado));
const maxProximasRows = computed(() => Math.min(50, Math.max(5, config.value.max_citas_proximas || 10)));
const proximaCitaPageCount = computed(() => Math.max(1, Math.ceil(allProximasCitas.value.length / maxProximasRows.value)));
const proximasCitas = computed(() => {
  const start = proximaCitaPage.value * maxProximasRows.value;
  return allProximasCitas.value.slice(start, start + maxProximasRows.value);
});
const effectiveDisplayMode = computed<DisplayMode>(() => {
  if (hasHighlightedTurnos.value) return 'turnos';
  if (config.value.mostrar_proxima_cita && !config.value.mostrar_turnos) return 'proxima_cita';
  return displayMode.value;
});

const doctorStatusOptions = [
  { value: 'AUSENTE', label: 'Ausente', tone: 'red', icon: 'x' },
  { value: 'NO_DISPONIBLE', label: 'No disponible', tone: 'orange', icon: '!' },
  { value: 'EN_CONSULTA', label: 'En consulta', tone: 'yellow', icon: '' },
  { value: 'DISPONIBLE', label: 'Disponible', tone: 'green', icon: '✓' },
  { value: 'NO_MOSTRAR', label: 'No mostrar', tone: 'muted', icon: '' },
];

function pollingMs() {
  const seconds = Math.min(60, Math.max(5, config.value.polling_interval_seconds || 5));
  return seconds * 1000;
}

function timestampMs(value: string) {
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) ? timestamp : 0;
}

function syncServerClock(value: string) {
  const serverNow = timestampMs(value);
  if (serverNow > 0) {
    serverClockOffsetMs = serverNow - Date.now();
  }
}

function currentServerTimeMs() {
  return Date.now() + serverClockOffsetMs;
}

function turnoHighlightExpiresAt(item: PublicDisplayTurno) {
  return timestampMs(item.llamado_en) + config.value.segundos_resaltado * 1000;
}

function turnoVisibleExpiresAt(item: PublicDisplayTurno) {
  return timestampMs(item.llamado_en) + config.value.segundos_visible * 1000;
}

function normalizeTurnoTimings(items: PublicDisplayTurno[]) {
  const now = currentServerTimeMs();
  return items
    .filter((item) => turnoVisibleExpiresAt(item) > now)
    .map((item) => (item.resaltado && turnoHighlightExpiresAt(item) <= now ? { ...item, resaltado: false } : item));
}

function refreshTurnoTimings() {
  const wasForcingTurnos = hasHighlightedTurnos.value;
  const previousTurnoCount = turnos.value.length;
  const nextTurnos = normalizeTurnoTimings(turnos.value);
  turnos.value = nextTurnos;
  const isRotatingDisplay = config.value.mostrar_turnos && config.value.mostrar_proxima_cita;
  if (
    !nextTurnos.some((item) => item.resaltado) &&
    (wasForcingTurnos || (isRotatingDisplay && previousTurnoCount > 0 && nextTurnos.length === 0))
  ) {
    syncDisplayMode(nextTurnos, false);
  }
  scheduleTurnoTimingRefresh();
}

function scheduleTurnoTimingRefresh() {
  window.clearTimeout(turnoTimingTimer);
  const now = currentServerTimeMs();
  const expirations = turnos.value.flatMap((item) => {
    const values = [turnoVisibleExpiresAt(item)];
    if (item.resaltado) {
      values.push(turnoHighlightExpiresAt(item));
    }
    return values.filter((value) => value > now);
  });
  if (!expirations.length) return;
  const nextExpiration = Math.min(...expirations);
  const delay = Math.max(250, nextExpiration - now + 100);
  turnoTimingTimer = window.setTimeout(refreshTurnoTimings, delay);
}

function storageAvailable() {
  try {
    window.localStorage.getItem(VOICE_SETTING_KEY);
    return true;
  } catch {
    return false;
  }
}

function loadVoicePreference() {
  voiceSupported.value = 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;
  if (!voiceSupported.value || !storageAvailable()) return;
  voiceEnabled.value = window.localStorage.getItem(VOICE_SETTING_KEY) === 'true';
}

function saveVoicePreference() {
  if (!storageAvailable()) return;
  window.localStorage.setItem(VOICE_SETTING_KEY, String(voiceEnabled.value));
}

function turnoKey(item: PublicDisplayTurno) {
  return `${item.turno}|${item.consultorio}|${item.texto ?? ''}|${item.llamado_en}`;
}

function turnoForSpeech(turno: string) {
  const clean = turno.trim();
  if (!/^[a-z0-9-]+$/i.test(clean)) return clean;
  return clean
    .split('')
    .map((char) => (char === '-' ? 'guion' : char))
    .join(' ');
}

function selectSpanishVoice() {
  const voices = window.speechSynthesis.getVoices();
  return (
    voices.find((voice) => voice.lang.toLowerCase() === 'es-mx') ??
    voices.find((voice) => voice.lang.toLowerCase().startsWith('es-')) ??
    null
  );
}

function speak(text: string) {
  if (!voiceSupported.value || !voiceEnabled.value || !text.trim()) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'es-MX';
  utterance.rate = 0.92;
  utterance.pitch = 1;
  const voice = selectSpanishVoice();
  if (voice) utterance.voice = voice;
  window.speechSynthesis.speak(utterance);
}

function displayText(item: PublicDisplayTurno) {
  return item.texto || '';
}

function speechText(item: PublicDisplayTurno) {
  if (!item.texto) {
    return `Turno ${turnoForSpeech(item.turno)}. Consultorio ${item.consultorio}.`;
  }
  return item.texto.replace(item.turno, turnoForSpeech(item.turno));
}

function announceTurnos(items: PublicDisplayTurno[]) {
  if (!items.length) return;
  const text = items.map(speechText).join(' ');
  speak(text);
}

function doctorStatusLabel(status: string) {
  return doctorStatusOptions.find((item) => item.value === status)?.label ?? status;
}

function doctorStatusTone(status: string) {
  return doctorStatusOptions.find((item) => item.value === status)?.tone ?? 'muted';
}

function doctorStatusIcon(status: string) {
  return doctorStatusOptions.find((item) => item.value === status)?.icon ?? '';
}

function estimatedTimeLabel(item: PublicDisplayProximaCita) {
  if (item.hora_estimada_proxima_cita) return item.hora_estimada_proxima_cita;
  if (!item.proxima_cita_estimada) return 'Sin estimar';
  return new Date(item.proxima_cita_estimada).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });
}

function currentTimeLabel() {
  return new Date(currentServerTimeMs()).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });
}

function updateClock() {
  currentTime.value = currentTimeLabel();
}

function availabilityLabel(status: string) {
  if (status === 'NO_MOSTRAR') return '';
  return doctorStatusLabel(status);
}

function clampProximaCitaPage() {
  proximaCitaPage.value = Math.min(proximaCitaPage.value, proximaCitaPageCount.value - 1);
}

function syncDisplayMode(responseTurnos: PublicDisplayTurno[], advanceProximaPage = true) {
  if (responseTurnos.some((item) => item.resaltado)) {
    displayMode.value = 'turnos';
    return;
  }
  clampProximaCitaPage();
  if (config.value.mostrar_turnos && config.value.mostrar_proxima_cita) {
    if (!advanceProximaPage) {
      if (displayMode.value === 'turnos') {
        displayMode.value = 'proxima_cita';
      }
      return;
    }
    if (displayMode.value === 'proxima_cita') {
      if (proximaCitaPage.value < proximaCitaPageCount.value - 1) {
        proximaCitaPage.value += 1;
        displayMode.value = 'proxima_cita';
      } else {
        proximaCitaPage.value = 0;
        displayMode.value = 'turnos';
      }
    } else {
      displayMode.value = 'proxima_cita';
    }
    return;
  }
  if (config.value.mostrar_proxima_cita) {
    if (advanceProximaPage) {
      proximaCitaPage.value =
        proximaCitaPage.value < proximaCitaPageCount.value - 1 ? proximaCitaPage.value + 1 : 0;
    }
    displayMode.value = 'proxima_cita';
    return;
  }
  displayMode.value = config.value.mostrar_proxima_cita ? 'proxima_cita' : 'turnos';
}

function toggleVoice() {
  if (!voiceSupported.value) return;
  voiceEnabled.value = !voiceEnabled.value;
  saveVoicePreference();
  if (voiceEnabled.value) {
    speak('Voz activada.');
  } else {
    window.speechSynthesis.cancel();
  }
}

async function loadData() {
  window.clearTimeout(timer);
  try {
    const response = await getPublicDisplayTurnos(codigoDispositivo.value, token.value);
    config.value = response.config;
    syncServerClock(response.ultima_conexion);
    updateClock();
    const responseTurnos = normalizeTurnoTimings(response.turnos);
    const nextKeys = new Set(responseTurnos.map(turnoKey));
    const newHighlightedTurnos = responseTurnos.filter(
      (item) => item.resaltado && !knownTurnoKeys.has(turnoKey(item)),
    );
    turnos.value = responseTurnos;
    allProximasCitas.value = response.proximas_citas ?? [];
    clampProximaCitaPage();
    syncDisplayMode(responseTurnos, hasLoadedTurnos && !responseTurnos.some((item) => item.resaltado));
    displayName.value = response.nombre || response.codigo_dispositivo;
    if (hasLoadedTurnos) {
      announceTurnos(newHighlightedTurnos);
    }
    knownTurnoKeys = nextKeys;
    hasLoadedTurnos = true;
    lastUpdate.value = new Date(response.ultima_conexion).toLocaleTimeString();
    connected.value = true;
    error.value = '';
  } catch (err) {
    connected.value = false;
    error.value = err instanceof Error ? err.message : 'Sin conexión';
  } finally {
    scheduleTurnoTimingRefresh();
    timer = window.setTimeout(loadData, pollingMs());
  }
}

onMounted(async () => {
  loadVoicePreference();
  updateClock();
  clockTimer = window.setInterval(updateClock, 1000);
  try {
    displayQr.value = await QRCode.toDataURL(window.location.href || codigoDispositivo.value, { margin: 1, width: 96 });
  } catch {
    displayQr.value = '';
  }
  await loadData();
});

onUnmounted(() => {
  window.clearTimeout(timer);
  window.clearTimeout(turnoTimingTimer);
  window.clearInterval(clockTimer);
  if (voiceSupported.value) {
    window.speechSynthesis.cancel();
  }
});
</script>

<template>
  <main class="display-shell" :style="screenStyle">
    <aside class="display-identity">
      <img v-if="displayQr" :src="displayQr" alt="QR del display" />
      <span>{{ displayName || codigoDispositivo }}</span>
    </aside>
    <header class="display-topbar">
      <div class="display-topbar-spacer" aria-hidden="true"></div>
      <h1 v-if="effectiveDisplayMode === 'proxima_cita'">Citas próximas</h1>
      <div class="display-status">
        <span :class="{ connected }">{{ connected ? 'Conectada' : 'Sin conexión' }}</span>
        <span v-if="lastUpdate">Última actualización: {{ lastUpdate }}</span>
        <button
          class="display-voice-button"
          type="button"
          :class="{ active: voiceEnabled }"
          :disabled="!voiceSupported"
          :aria-pressed="voiceEnabled"
          :title="voiceSupported ? (voiceEnabled ? 'Silenciar voz' : 'Activar voz') : 'Voz no disponible en este navegador'"
          @click="toggleVoice"
        >
          <svg aria-hidden="true" viewBox="0 0 24 24">
            <path d="M4 9v6h4l5 4V5L8 9H4Z" />
            <path v-if="voiceEnabled" d="M16 8.5a5 5 0 0 1 0 7M18.5 6a8.5 8.5 0 0 1 0 12" />
            <path v-else d="m17 9 4 6M21 9l-4 6" />
          </svg>
          <span>{{ voiceEnabled ? 'Voz activa' : 'Voz apagada' }}</span>
        </button>
        <time class="display-clock">{{ currentTime }}</time>
      </div>
    </header>

    <section v-if="effectiveDisplayMode === 'turnos'" class="turnos-stage" aria-live="polite">
      <article
        v-for="item in turnos"
        :key="`${item.turno}-${item.llamado_en}`"
        class="turno-card"
        :class="{ highlighted: item.resaltado, 'text-only': displayText(item) }"
      >
        <span v-if="displayText(item)" class="turno-card-text">{{ displayText(item) }}</span>
        <template v-else>
          <strong>{{ item.turno }}</strong>
          <span>{{ item.consultorio }}</span>
        </template>
      </article>
      <p v-if="turnos.length === 0" class="display-empty">Sin citas llamadas</p>
    </section>
    <section v-else class="next-appointments-stage" aria-live="polite">
      <div v-if="proximasCitas.length > 0" class="next-appointments-table-wrap">
        <table class="next-appointments-table">
          <colgroup>
            <col class="next-appointments-consultorio" />
            <col class="next-appointments-medico" />
            <col class="next-appointments-disponibilidad" />
            <col class="next-appointments-cita" />
            <col class="next-appointments-hora" />
          </colgroup>
          <thead>
            <tr>
              <th>Consultorio</th>
              <th>Médico</th>
              <th>Disponibilidad</th>
              <th>Cita</th>
              <th>Hora aprox.</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in proximasCitas" :key="`${item.folio_turno}-${item.medico_id}-${index}`">
              <td>{{ item.consultorio }}</td>
              <td>{{ item.medico }}</td>
              <td>
                <span v-if="availabilityLabel(item.estado_atencion)" class="doctor-status-value next-appointment-status">
                  <span class="doctor-status-icon" :class="`doctor-status-${doctorStatusTone(item.estado_atencion)}`">
                    {{ doctorStatusIcon(item.estado_atencion) }}
                  </span>
                  {{ availabilityLabel(item.estado_atencion) }}
                </span>
              </td>
              <td><strong>{{ item.folio_turno }}</strong></td>
              <td><time>{{ estimatedTimeLabel(item) }}</time></td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="proximasCitas.length === 0" class="display-empty">Sin citas próximas estimadas</p>
    </section>

    <footer v-if="error" class="display-error">{{ error }}</footer>
  </main>
</template>
