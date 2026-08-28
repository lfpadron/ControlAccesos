<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import {
  getCurrentUser,
  listMedicosEstado,
  updateMedicoEstado,
  type MedicoEstado,
  type Usuario,
} from '../api/client';

const medicos = ref<MedicoEstado[]>([]);
const currentUser = ref<Usuario | null>(null);
const selectedMedicoId = ref('');
const medicoSearch = ref('');
const notas = ref('');
const loading = ref(true);
const saving = ref(false);
const error = ref('');
const message = ref('');

const statusOptions = [
  { value: 'AUSENTE', label: 'Ausente', tone: 'red', icon: 'x' },
  { value: 'NO_DISPONIBLE', label: 'No disponible', tone: 'orange', icon: '!' },
  { value: 'EN_CONSULTA', label: 'En consulta', tone: 'yellow', icon: '' },
  { value: 'DISPONIBLE', label: 'Disponible', tone: 'green', icon: '✓' },
];

const selectedMedico = computed(() => medicos.value.find((medico) => medico.id === selectedMedicoId.value) ?? null);
const isDoctorUser = computed(() => currentUser.value?.role_codes?.includes('MEDICO') ?? false);
const medicoLocked = computed(() => isDoctorUser.value);
const remainingNotes = computed(() => Math.max(0, 100 - notas.value.length));

function medicoLabel(medico: MedicoEstado) {
  return medico.nombre_visible || `${medico.nombre} ${medico.apellidos}`.trim();
}

function statusLabel(status: string) {
  return statusOptions.find((item) => item.value === status)?.label ?? status;
}

function statusTone(status: string) {
  return statusOptions.find((item) => item.value === status)?.tone ?? 'muted';
}

function statusIcon(status: string) {
  return statusOptions.find((item) => item.value === status)?.icon ?? '';
}

function normalize(value: string) {
  return value.trim().toLowerCase();
}

function selectMedico(medico: MedicoEstado | null) {
  selectedMedicoId.value = medico?.id ?? '';
  medicoSearch.value = medico ? medicoLabel(medico) : '';
  notas.value = medico?.notas_estado ?? '';
}

function syncMedicoFromSearch() {
  const target = normalize(medicoSearch.value);
  const match = medicos.value.find((medico) => normalize(medicoLabel(medico)) === target);
  if (match) {
    selectMedico(match);
  } else {
    selectedMedicoId.value = '';
    notas.value = '';
  }
}

function preferredMedico(rows: MedicoEstado[]) {
  if (isDoctorUser.value) {
    return rows.find((medico) => medico.usuario_id === currentUser.value?.id) ?? rows[0] ?? null;
  }
  if (rows.length === 1) return rows[0];
  return rows.find((medico) => medico.id === selectedMedicoId.value) ?? null;
}

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const [userData, medicosData] = await Promise.all([getCurrentUser(), listMedicosEstado()]);
    currentUser.value = userData;
    medicos.value = medicosData;
    selectMedico(preferredMedico(medicosData));
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar médicos.';
  } finally {
    loading.value = false;
  }
}

async function setEstado(estado: string) {
  const medico = selectedMedico.value;
  if (!medico) {
    error.value = 'Seleccione un médico.';
    return;
  }
  if (notas.value.length > 100) {
    error.value = 'Las notas deben tener máximo 100 caracteres.';
    return;
  }
  saving.value = true;
  error.value = '';
  message.value = '';
  try {
    const updated = await updateMedicoEstado(medico.id, {
      estado_atencion: estado,
      notas_estado: notas.value.trim() || null,
    });
    medicos.value = medicos.value.map((item) => (item.id === updated.id ? updated : item));
    selectMedico(updated);
    message.value = `Estado actualizado: ${statusLabel(updated.estado_atencion)}.`;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible actualizar el estado.';
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1>Estado del médico</h1>
        <p>Actualiza si el médico está atendiendo o ausente.</p>
      </div>
      <button class="secondary" type="button" :disabled="loading" @click="load">Actualizar</button>
    </div>

    <div class="panel form doctor-status-panel">
      <div class="form-row">
        <label for="estado-medico-search">Médico</label>
        <input
          id="estado-medico-search"
          v-model="medicoSearch"
          list="estado-medico-options"
          :disabled="loading || medicoLocked"
          placeholder="Buscar médico"
          @input="syncMedicoFromSearch"
          @change="syncMedicoFromSearch"
        />
        <datalist id="estado-medico-options">
          <option v-for="medico in medicos" :key="medico.id" :value="medicoLabel(medico)" />
        </datalist>
      </div>

      <p v-if="loading" class="message">Cargando médicos...</p>
      <p v-if="message" class="success-message">{{ message }}</p>
      <p v-if="error" class="error">{{ error }}</p>

      <div v-if="selectedMedico" class="doctor-status-summary">
        <div>
          <span>Médico</span>
          <strong>{{ medicoLabel(selectedMedico) }}</strong>
        </div>
        <div>
          <span>Estado actual</span>
          <strong class="doctor-status-value">
            <span class="doctor-status-icon" :class="`doctor-status-${statusTone(selectedMedico.estado_atencion)}`">
              {{ statusIcon(selectedMedico.estado_atencion) }}
            </span>
            {{ statusLabel(selectedMedico.estado_atencion) }}
          </strong>
        </div>
      </div>

      <div class="form-row">
        <label for="estado-medico-notas">Notas</label>
        <textarea id="estado-medico-notas" v-model="notas" maxlength="100" rows="3" placeholder="Notas opcionales" />
        <div class="notes-footer">
          <span>{{ remainingNotes }} caracteres disponibles</span>
          <button class="small secondary" type="button" @click="notas = ''">Limpiar</button>
        </div>
      </div>

      <div class="doctor-status-actions">
        <button
          v-for="statusOption in statusOptions"
          :key="statusOption.value"
          class="doctor-status-button"
          type="button"
          :disabled="saving || !selectedMedico"
          @click="setEstado(statusOption.value)"
        >
          <span class="doctor-status-icon" :class="`doctor-status-${statusOption.tone}`">{{ statusOption.icon }}</span>
          {{ statusOption.label }}
        </button>
      </div>

      <p v-if="!loading && medicos.length === 0" class="message">No hay médicos disponibles para este usuario.</p>
    </div>
  </section>
</template>
