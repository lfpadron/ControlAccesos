<script setup lang="ts">
import { ref } from 'vue';
import { checkinQr, type CheckinResponse } from '../api';

defineEmits<{
  back: [];
}>();

const token = ref('');
const result = ref<CheckinResponse | null>(null);
const error = ref('');
const loading = ref(false);

async function submit() {
  if (!token.value.trim()) return;
  loading.value = true;
  error.value = '';
  try {
    result.value = await checkinQr(token.value.trim());
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible validar el QR.';
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <section class="screen">
    <form class="placeholder" @submit.prevent="submit">
      <div class="scan-box">Cámara pendiente</div>
      <label for="qr">Token QR</label>
      <input id="qr" v-model="token" placeholder="Pegar token" />
      <button class="primary" type="submit" :disabled="loading">Registrar llegada</button>
      <div v-if="result" class="result" :class="result.resultado.toLowerCase()">
        <strong>{{ result.resultado }}</strong>
        <span>{{ result.mensaje }}</span>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
    </form>
    <button class="secondary" type="button" @click="$emit('back')">Volver</button>
  </section>
</template>
