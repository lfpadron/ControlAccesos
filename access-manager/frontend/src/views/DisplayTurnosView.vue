<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import QRCode from 'qrcode';
import { getPublicDisplayTurnos, PublicDisplayConfig, PublicDisplayTurno } from '../api/client';

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
let timer: number | undefined;

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

async function loadData() {
  window.clearTimeout(timer);
  try {
    const response = await getPublicDisplayTurnos(codigoDispositivo.value, token.value);
    config.value = response.config;
    turnos.value = response.turnos;
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
  try {
    displayQr.value = await QRCode.toDataURL(window.location.href || codigoDispositivo.value, { margin: 1, width: 96 });
  } catch {
    displayQr.value = '';
  }
  await loadData();
});

onUnmounted(() => {
  window.clearTimeout(timer);
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
