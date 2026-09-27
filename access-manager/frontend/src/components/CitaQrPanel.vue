<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import { getTicket, prepareCitaQr, sendCitaQr, type Cita, type QrDeliveryMethod, type QrPreview, type TicketResponse } from '../api/client';
import TelegramLink from './TelegramLink.vue';

const props = defineProps<{ cita: Cita; canSend: boolean; ticketMode?: boolean; refreshKey: number }>();
const emit = defineEmits<{ prepared: [data: QrPreview]; close: [] }>();
const panel = ref<HTMLElement | null>(null);
const preview = ref<QrPreview | null>(null);
const ticket = ref<TicketResponse | null>(null);
const loading = ref(false);
const sending = ref(false);
const choosing = ref(false);
const linking = ref(false);
const selectedMethod = ref<QrDeliveryMethod | 'BAJAR' | ''>('');
const error = ref('');
const message = ref('');
let requestVersion = 0;
const blocked = computed(() => ['CANCELADA', 'EXPIRADA', 'NO_LLEGO'].includes(props.cita.estado));
const imageUrl = computed(() => preview.value ? `data:image/png;base64,${preview.value.imagen_base64}` : '');
const selectedDestination = computed(() => preview.value?.destinos.find((item) => item.metodo === selectedMethod.value));
const canConfirm = computed(() => !loading.value && !sending.value && !blocked.value && Boolean(preview.value)
  && (selectedMethod.value === 'BAJAR' || (props.canSend && selectedDestination.value?.disponible)));

async function refresh(scroll = false) {
  const version = ++requestVersion;
  const citaId = props.cita.id;
  loading.value = true;
  error.value = '';
  message.value = '';
  preview.value = null;
  ticket.value = null;
  selectedMethod.value = '';
  try {
    const data = await prepareCitaQr(citaId);
    const ticketData = props.ticketMode ? await getTicket(citaId) : null;
    if (version !== requestVersion) return;
    preview.value = data;
    ticket.value = ticketData;
    const preferred = data.destinos.find((item) => item.metodo === data.metodo_preferido && item.disponible);
    selectedMethod.value = preferred?.metodo ?? '';
    linking.value = false;
    emit('prepared', data);
  } catch (err) {
    if (version === requestVersion) error.value = err instanceof Error ? err.message : 'No fue posible preparar el QR.';
  } finally {
    if (version === requestVersion) {
      loading.value = false;
      if (scroll) {
        await nextTick();
        panel.value?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        panel.value?.focus({ preventScroll: true });
      }
    }
  }
}

watch(() => [props.cita.id, props.refreshKey, props.ticketMode], () => {
  choosing.value = false;
  linking.value = false;
  sending.value = false;
  void refresh(true);
}, { immediate: true });
watch(blocked, (value) => { if (value) { choosing.value = false; linking.value = false; } });

function download() {
  if (!preview.value || blocked.value) return;
  const link = document.createElement('a');
  link.href = imageUrl.value;
  link.download = preview.value.nombre_archivo;
  link.click();
}

async function confirm() {
  if (!canConfirm.value || !preview.value || !selectedMethod.value) return;
  if (selectedMethod.value === 'BAJAR') {
    download();
    choosing.value = false;
    return;
  }
  const version = requestVersion;
  sending.value = true;
  error.value = '';
  message.value = '';
  try {
    const result = await sendCitaQr(props.cita.id, preview.value, selectedMethod.value);
    if (version === requestVersion) { message.value = result.mensaje; choosing.value = false; }
  } catch (err) {
    if (version === requestVersion) error.value = err instanceof Error ? err.message : 'No fue posible enviar el QR.';
  } finally {
    if (version === requestVersion) sending.value = false;
  }
}
</script>

<template>
  <section ref="panel" class="panel qr-delivery-panel" tabindex="-1" aria-label="QR de la cita" :aria-busy="loading || sending">
    <div class="page-header compact">
      <h2>{{ ticketMode ? 'Ticket lógico' : 'QR de la cita' }}</h2>
      <button class="secondary" type="button" :disabled="sending" @click="emit('close')">Cerrar</button>
    </div>
    <p><strong>{{ preview?.paciente || cita.paciente }}</strong> · {{ cita.fecha_cita }} {{ cita.hora_cita.slice(0, 5) }} · Turno {{ cita.folio_turno }}</p>
    <p v-if="blocked" class="error">El estado de esta cita no permite compartir su QR.</p>
    <p v-if="loading" role="status">Preparando QR…</p>
    <div v-if="preview && !blocked" class="qr-preview">
      <img :src="imageUrl" alt="QR de acceso de la cita seleccionada" />
      <div class="qr-actions">
        <button type="button" :disabled="!canSend || loading || sending" @click="choosing = !choosing; linking = false; message = ''; error = ''">Enviar QR</button>
        <button class="secondary" type="button" :disabled="loading || sending" @click="download">Bajar</button>
      </div>
    </div>
    <form v-if="choosing && preview && !blocked" class="qr-destinations" @submit.prevent="confirm">
      <fieldset :disabled="sending || loading">
        <legend>Selecciona el destino</legend>
        <label class="qr-option"><input v-model="selectedMethod" type="radio" value="BAJAR" name="qr-destination" /> Bajar</label>
        <div v-for="destination in preview.destinos" :key="destination.metodo" class="qr-option-row">
          <label class="qr-option">
            <input v-model="selectedMethod" type="radio" :value="destination.metodo" name="qr-destination" :disabled="!destination.disponible" />
            {{ destination.etiqueta }}
          </label>
          <small v-if="destination.motivo">{{ destination.motivo }}</small>
          <button v-if="destination.vinculable && !destination.disponible" class="small secondary" type="button" @click="linking = true">Vincular Telegram</button>
        </div>
      </fieldset>
      <p v-if="!preview.destinos.length">El paciente no tiene correo ni celulares registrados. Puedes bajar el QR.</p>
      <div class="actions-row">
        <button type="submit" :disabled="!canConfirm">{{ sending ? 'Enviando…' : 'Confirmar' }}</button>
        <button class="secondary" type="button" :disabled="sending" @click="choosing = false; linking = false; selectedMethod = ''">Cancelar</button>
      </div>
    </form>
    <TelegramLink v-if="linking && preview?.telegram_bot_url && !blocked" :url="preview.telegram_bot_url" />
    <button class="secondary" type="button" :disabled="loading || sending || blocked" @click="refresh()">Actualizar QR y destinos</button>
    <pre v-if="ticket && !blocked">{{ ticket.encabezado_fecha }}
{{ ticket.leyenda }}
Turno {{ ticket.turno }}
Consultorio {{ ticket.consultorio }}
Torre {{ ticket.torre }}
{{ ticket.piso }}
Cita {{ ticket.hora }} hrs</pre>
    <p v-if="message" class="message" role="status">{{ message }}</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
  </section>
</template>

<style scoped>
.qr-delivery-panel { scroll-margin-top: 1rem; }
.qr-actions { display: flex; flex-wrap: wrap; gap: .75rem; align-items: center; }
.qr-destinations { margin: 1rem 0; }
.qr-destinations fieldset { border: 1px solid #ccd5e0; border-radius: 8px; padding: 1rem; min-width: 0; }
.qr-option-row { margin: .75rem 0; display: grid; gap: .35rem; justify-items: start; }
.qr-option { display: flex; align-items: center; gap: .5rem; overflow-wrap: anywhere; }
.qr-option input { width: auto; flex-shrink: 0; }
.qr-preview img { max-width: min(100%, 480px); height: auto; }
</style>
