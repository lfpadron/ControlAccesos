<script setup lang="ts">
import { ref } from 'vue';
import { checkinLobby, searchCitas, type CheckinResponse, type CitaSearchResult } from '../api';

defineEmits<{
  back: [];
}>();

const query = ref('');
const citas = ref<CitaSearchResult[]>([]);
const result = ref<CheckinResponse | null>(null);
const error = ref('');
const loading = ref(false);

async function search() {
  if (!query.value.trim()) return;
  loading.value = true;
  error.value = '';
  result.value = null;
  try {
    citas.value = await searchCitas(query.value.trim());
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible buscar citas.';
  } finally {
    loading.value = false;
  }
}

async function checkin(citaId: string) {
  loading.value = true;
  error.value = '';
  try {
    result.value = await checkinLobby(citaId);
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible registrar llegada.';
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <section class="screen">
    <form class="placeholder" @submit.prevent="search">
      <label for="patient">Buscar cita de hoy</label>
      <input id="patient" v-model="query" placeholder="Nombre o teléfono" />
      <button class="primary" type="submit" :disabled="loading">Buscar</button>
      <div class="mobile-list">
        <button v-for="cita in citas" :key="cita.id" class="list-item" type="button" @click="checkin(cita.id)">
          <strong>{{ cita.folio_turno }}</strong>
          <span>{{ cita.hora_cita.slice(0, 5) }} · {{ cita.consultorio || 'Consultorio' }} · {{ cita.piso || 'Piso' }}</span>
        </button>
      </div>
      <div v-if="result" class="result" :class="result.resultado.toLowerCase()">
        <strong>{{ result.resultado }}</strong>
        <span>{{ result.mensaje }}</span>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
    </form>
    <button class="secondary" type="button" @click="$emit('back')">Volver</button>
  </section>
</template>
