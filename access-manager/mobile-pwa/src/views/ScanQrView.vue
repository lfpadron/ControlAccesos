<script setup lang="ts">
import { ref } from 'vue';
import { checkinQr, validateQr, type CheckinResponse } from '../api';

defineEmits<{
  back: [];
}>();

const token = ref('');
const pendingToken = ref('');
const result = ref<CheckinResponse | null>(null);
const error = ref('');
const loading = ref(false);
const confirming = ref(false);

async function submit() {
  if (!token.value.trim()) return;
  loading.value = true;
  error.value = '';
  try {
    const response = await validateQr(token.value.trim());
    result.value = response;
    pendingToken.value = response.requiere_confirmacion ? token.value.trim() : '';
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible validar el QR.';
  } finally {
    loading.value = false;
  }
}

async function confirm() {
  if (!pendingToken.value) return;
  confirming.value = true;
  error.value = '';
  try {
    result.value = await checkinQr(pendingToken.value);
    pendingToken.value = '';
    token.value = '';
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible registrar el check-in.';
  } finally {
    confirming.value = false;
  }
}
</script>

<template>
  <section class="screen">
    <form class="placeholder" @submit.prevent="submit">
      <div class="scan-box">Cámara pendiente</div>
      <label for="qr">Token QR</label>
      <input id="qr" v-model="token" placeholder="Pegar token" />
      <button class="primary" type="submit" :disabled="loading">Validar</button>
      <div v-if="result" class="result" :class="result.resultado.toLowerCase()">
        <strong>{{ result.resultado === 'ROJO' ? '✕' : '✓' }} {{ result.mensaje }}</strong>
        <span v-if="result.fecha_label">{{ result.fecha_label }}</span>
        <span v-if="result.torre || result.piso">{{ [result.torre, result.piso].filter(Boolean).join(' · ') }}</span>
        <button v-if="result.requiere_confirmacion" class="primary" type="button" :disabled="confirming" @click="confirm">
          {{ confirming ? 'Registrando...' : '✓ Confirmar' }}
        </button>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
    </form>
    <button class="secondary" type="button" @click="$emit('back')">Volver</button>
  </section>
</template>
