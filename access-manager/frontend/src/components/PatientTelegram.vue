<script setup lang="ts">
import { ref, watch } from 'vue';
import { getPatientTelegram, unlinkPatientTelegram, type TelegramPatientStatus } from '../api/client';
import TelegramLink from './TelegramLink.vue';

const props = defineProps<{ patientId: string; canEdit: boolean }>();
const status = ref<TelegramPatientStatus | null>(null);
const loading = ref(false);
const error = ref('');
const linking = ref(false);
const pendingUnlink = ref<1 | 2 | null>(null);
let version = 0;

async function load() {
  const current = ++version;
  loading.value = true;
  error.value = '';
  try {
    const data = await getPatientTelegram(props.patientId);
    if (current === version) status.value = data;
  } catch (err) {
    if (current === version) error.value = err instanceof Error ? err.message : 'No fue posible consultar Telegram.';
  } finally {
    if (current === version) loading.value = false;
  }
}

async function unlink() {
  if (!pendingUnlink.value || !props.canEdit || loading.value) return;
  const current = ++version;
  loading.value = true;
  error.value = '';
  try {
    const data = await unlinkPatientTelegram(props.patientId, pendingUnlink.value);
    if (current === version) { status.value = data; pendingUnlink.value = null; }
  } catch (err) {
    if (current === version) error.value = err instanceof Error ? err.message : 'No fue posible desvincular Telegram.';
  } finally {
    if (current === version) loading.value = false;
  }
}

watch(() => props.patientId, () => {
  status.value = null;
  linking.value = false;
  pendingUnlink.value = null;
  void load();
}, { immediate: true });
</script>

<template>
  <div class="telegram-patient" :aria-busy="loading">
    <h3>Telegram</h3>
    <p class="message">La vinculación utiliza los celulares guardados. Guarda primero cualquier cambio de teléfono.</p>
    <p v-if="status && !status.bot_url">Telegram aún no está configurado.</p>
    <p v-if="status && !status.contactos.length">No hay celulares registrados para vincular.</p>
    <div v-for="contact in status?.contactos ?? []" :key="contact.posicion" class="inline-actions">
      <span>{{ contact.etiqueta }} — {{ contact.vinculado ? 'Vinculado' : 'Sin vincular' }}</span>
      <button v-if="contact.vinculado && canEdit" class="small secondary" type="button" :disabled="loading" @click="pendingUnlink = contact.posicion">Desvincular</button>
    </div>
    <div v-if="pendingUnlink" class="actions-row">
      <span>¿Desvincular Telegram del celular {{ pendingUnlink }} de este paciente?</span>
      <button type="button" :disabled="loading" @click="unlink">Confirmar</button>
      <button class="secondary" type="button" :disabled="loading" @click="pendingUnlink = null">Cancelar</button>
    </div>
    <div class="actions-row">
      <button v-if="status?.bot_url && status.contactos.length && canEdit" class="secondary" type="button" @click="linking = !linking">Vincular Telegram</button>
      <button class="secondary" type="button" :disabled="loading" @click="load">Actualizar</button>
    </div>
    <TelegramLink v-if="linking && status?.bot_url" :url="status.bot_url" />
    <p v-if="error" class="error" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
.telegram-patient { margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #ccd5e0; }
</style>
