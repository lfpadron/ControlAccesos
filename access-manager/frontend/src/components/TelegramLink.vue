<script setup lang="ts">
import { ref, watch } from 'vue';
import QRCode from 'qrcode';

const props = defineProps<{ url: string }>();
const code = ref('');
const copied = ref(false);
watch(() => props.url, async (url) => {
  code.value = '';
  copied.value = false;
  const result = await QRCode.toDataURL(url, { margin: 4, width: 200 });
  if (url === props.url) code.value = result;
}, { immediate: true });

async function copyLink() {
  try {
    await navigator.clipboard.writeText(props.url);
    copied.value = true;
  } catch {
    copied.value = false;
  }
}
</script>

<template>
  <div class="telegram-link">
    <p>El paciente debe abrir este enlace en su Telegram, pulsar <strong>Iniciar</strong> y <strong>Compartir mi celular</strong>. Debe usar el celular registrado en CMC.</p>
    <img v-if="code" :src="code" alt="Enlace para vincular Telegram; no es el QR de acceso" width="200" height="200" />
    <p><a :href="url" target="_blank" rel="noopener noreferrer">{{ url }}</a></p>
    <button class="secondary" type="button" @click="copyLink">{{ copied ? 'Enlace copiado' : 'Copiar enlace' }}</button>
    <p class="message">Después de compartir el celular, pulsa Actualizar. Este código sólo vincula Telegram; no permite el acceso a la cita.</p>
  </div>
</template>

<style scoped>
.telegram-link { padding: 1rem; border: 1px solid #ccd5e0; border-radius: 8px; }
.telegram-link p { overflow-wrap: anywhere; }
</style>
