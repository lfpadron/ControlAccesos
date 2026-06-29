<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import QRCode from 'qrcode';
import { getPublicDisplayTurnos, PublicDisplayConfig, PublicDisplayTurno } from '../api/client';

const VOICE_SETTING_KEY = 'access_manager_display_voice_enabled';

const route = useRoute();
const codigoDispositivo = computed(() => String(route.params.codigo_dispositivo ?? ''));
const token = computed(() => (typeof route.query.token === 'string' ? route.query.token : undefined));
const turnos = ref<PublicDisplayTurno[]>([]);
const config = ref<PublicDisplayConfig>({
  polling_interval_seconds: 5,
  segundos_resaltado: 25,
  segundos_visible: 300,
  max_turnos_visibles: 10,
});
const connected = ref(false);
const lastUpdate = ref('');
const error = ref('');
const displayQr = ref('');
const voiceSupported = ref(false);
const voiceEnabled = ref(false);
let timer: number | undefined;
let knownTurnoKeys = new Set<string>();
let hasLoadedTurnos = false;

const screenStyle = computed(() => ({
  '--display-bg': config.value.color_fondo || '#06111f',
  '--display-text': config.value.color_texto || '#f8fbff',
  '--display-new': config.value.color_turno_nuevo || '#34d399',
  '--display-normal': config.value.color_turno_normal || '#f8fbff',
  '--display-new-size': `${config.value.font_size_turno_nuevo || 96}px`,
  '--display-normal-size': `${config.value.font_size_turno_normal || 64}px`,
}));

function pollingMs() {
  const seconds = Math.min(10, Math.max(2, config.value.polling_interval_seconds || 5));
  return seconds * 1000;
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
  return `${item.turno}|${item.consultorio}|${item.llamado_en}`;
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

function announceTurnos(items: PublicDisplayTurno[]) {
  if (!items.length) return;
  const text = items
    .map((item) => `Turno ${turnoForSpeech(item.turno)}. Consultorio ${item.consultorio}.`)
    .join(' ');
  speak(text);
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
    const nextKeys = new Set(response.turnos.map(turnoKey));
    const newHighlightedTurnos = response.turnos.filter(
      (item) => item.resaltado && !knownTurnoKeys.has(turnoKey(item)),
    );
    config.value = response.config;
    turnos.value = response.turnos;
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
    timer = window.setTimeout(loadData, pollingMs());
  }
}

onMounted(async () => {
  loadVoicePreference();
  try {
    displayQr.value = await QRCode.toDataURL(window.location.href || codigoDispositivo.value, { margin: 1, width: 96 });
  } catch {
    displayQr.value = '';
  }
  await loadData();
});

onUnmounted(() => {
  window.clearTimeout(timer);
  if (voiceSupported.value) {
    window.speechSynthesis.cancel();
  }
});
</script>

<template>
  <main class="display-shell" :style="screenStyle">
    <aside class="display-identity">
      <img v-if="displayQr" :src="displayQr" alt="QR del display" />
      <span>{{ codigoDispositivo }}</span>
    </aside>
    <header class="display-status">
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
    </header>

    <section class="turnos-stage" aria-live="polite">
      <article v-for="item in turnos" :key="`${item.turno}-${item.llamado_en}`" class="turno-card" :class="{ highlighted: item.resaltado }">
        <strong>{{ item.turno }}</strong>
        <span>{{ item.consultorio }}</span>
      </article>
      <p v-if="turnos.length === 0" class="display-empty">Sin turnos llamados</p>
    </section>

    <footer v-if="error" class="display-error">{{ error }}</footer>
  </main>
</template>
