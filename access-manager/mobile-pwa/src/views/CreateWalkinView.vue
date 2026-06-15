<script setup lang="ts">
import { reactive, ref } from 'vue';
import { apiFetch } from '../api';

defineEmits<{
  back: [];
}>();

function todayLocalIso() {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

const form = reactive({
  token: localStorage.getItem('access_manager_token') ?? '',
  paciente_id: '',
  medico_id: '',
  consultorio_id: '',
  complejo_id: '',
  piso_id: '',
  fecha_cita: todayLocalIso(),
  hora_cita: '09:00',
});
const message = ref('');
const error = ref('');
const loading = ref(false);

async function submit() {
  loading.value = true;
  error.value = '';
  message.value = '';
  try {
    localStorage.setItem('access_manager_token', form.token);
    await apiFetch(
      '/citas',
      {
        method: 'POST',
        body: JSON.stringify({
          tipo: 'ESPONTANEA',
          paciente_id: form.paciente_id,
          medico_id: form.medico_id,
          consultorio_id: form.consultorio_id,
          complejo_id: form.complejo_id,
          piso_id: form.piso_id,
          fecha_cita: form.fecha_cita,
          hora_cita: form.hora_cita,
          origen: 'APP_MOVIL',
        }),
      },
      form.token,
    );
    message.value = 'Cita espontánea creada.';
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible crear la cita.';
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <section class="screen">
    <form class="placeholder" @submit.prevent="submit">
      <label for="token">Token de sesión operativa</label>
      <input id="token" v-model="form.token" placeholder="Bearer token" />
      <label for="paciente">Paciente ID</label>
      <input id="paciente" v-model="form.paciente_id" required />
      <label for="medico">Médico ID</label>
      <input id="medico" v-model="form.medico_id" required />
      <label for="consultorio">Consultorio ID</label>
      <input id="consultorio" v-model="form.consultorio_id" required />
      <label for="complejo">Complejo ID</label>
      <input id="complejo" v-model="form.complejo_id" required />
      <label for="piso">Piso ID</label>
      <input id="piso" v-model="form.piso_id" required />
      <button class="primary" type="submit" :disabled="loading">Crear cita</button>
      <p v-if="message" class="message">{{ message }}</p>
      <p v-if="error" class="error">{{ error }}</p>
    </form>
    <button class="secondary" type="button" @click="$emit('back')">Volver</button>
  </section>
</template>
