<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { listMedicos, listUsuarios, updateMedico, type Medico, type Usuario } from '../api/client';
import { turnoTemplateOptions } from '../catalogs';

const medicos = ref<Medico[]>([]);
const usuarios = ref<Usuario[]>([]);
const query = ref('');
const selected = ref<Medico | null>(null);
const selectedTemplate = ref('');
const loading = ref(false);
const saving = ref(false);
const error = ref('');
const message = ref('');

function normalize(value: string | null | undefined) {
  return (value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

function usuarioForMedico(medico: Medico) {
  if (!medico.usuario_id) return null;
  return usuarios.value.find((usuario) => usuario.id === medico.usuario_id) ?? null;
}

function medicoCorreo(medico: Medico) {
  return usuarioForMedico(medico)?.email ?? '-';
}

function medicoEstado(medico: Medico) {
  return medico.activo ? 'Activo' : 'Inactivo';
}

function templateLabel(value: string) {
  return turnoTemplateOptions.find((option) => option.value === value)?.label ?? value;
}

const filteredMedicos = computed(() => {
  const needle = normalize(query.value);
  const sorted = [...medicos.value].sort((left, right) => {
    const leftLabel = `${left.apellidos} ${left.nombre}`.toLocaleLowerCase('es-MX');
    const rightLabel = `${right.apellidos} ${right.nombre}`.toLocaleLowerCase('es-MX');
    return leftLabel.localeCompare(rightLabel, 'es-MX');
  });
  if (!needle) return sorted;
  return sorted.filter((medico) => {
    const haystack = normalize(`${medico.apellidos} ${medico.nombre} ${medicoCorreo(medico)}`);
    return haystack.includes(needle);
  });
});

function selectMedico(medico: Medico) {
  selected.value = medico;
  selectedTemplate.value = medico.plantilla_turno;
  message.value = '';
  error.value = '';
}

async function loadData() {
  loading.value = true;
  error.value = '';
  try {
    const [medicosData, usuariosData] = await Promise.all([listMedicos(), listUsuarios()]);
    medicos.value = medicosData;
    usuarios.value = usuariosData;
    if (selected.value) {
      const refreshed = medicosData.find((medico) => medico.id === selected.value?.id) ?? null;
      selected.value = refreshed;
      selectedTemplate.value = refreshed?.plantilla_turno ?? '';
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar médicos.';
  } finally {
    loading.value = false;
  }
}

async function saveTemplate() {
  if (!selected.value || !selectedTemplate.value) return;
  saving.value = true;
  error.value = '';
  message.value = '';
  try {
    const saved = await updateMedico(selected.value.id, { plantilla_turno: selectedTemplate.value });
    medicos.value = medicos.value.map((medico) => (medico.id === saved.id ? saved : medico));
    selected.value = saved;
    selectedTemplate.value = saved.plantilla_turno;
    message.value = 'Plantilla de turnos actualizada.';
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible guardar la plantilla.';
  } finally {
    saving.value = false;
  }
}

onMounted(loadData);
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Plantilla de turnos</h1>
        <p>Asociación de formato de llamada para médicos.</p>
      </div>
    </header>

    <section class="panel">
      <div class="form-grid">
        <div class="form-row">
          <label for="plantilla-medico-search">Buscar médico</label>
          <input
            id="plantilla-medico-search"
            v-model="query"
            autocomplete="off"
            placeholder="Apellido, nombre o correo"
          />
        </div>
      </div>
    </section>

    <div class="grid catalog-grid">
      <section class="panel table-panel">
        <div class="actions-row">
          <h2>Médicos</h2>
          <button class="secondary" type="button" :disabled="loading" @click="loadData">
            {{ loading ? 'Cargando...' : 'Actualizar' }}
          </button>
        </div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Apellido(s)</th>
                <th>Nombre</th>
                <th>Correo</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="medico in filteredMedicos"
                :key="medico.id"
                class="selectable-row"
                :class="{ selected: selected?.id === medico.id }"
                @click="selectMedico(medico)"
              >
                <td>{{ medico.apellidos }}</td>
                <td>{{ medico.nombre }}</td>
                <td>{{ medicoCorreo(medico) }}</td>
                <td>{{ medicoEstado(medico) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="!loading && filteredMedicos.length === 0" class="message">No hay médicos para mostrar.</p>
      </section>

      <form class="panel form" @submit.prevent="saveTemplate">
        <h2>Plantilla</h2>
        <template v-if="selected">
          <div class="form-grid">
            <div class="form-row">
              <label>Apellido(s)</label>
              <input :value="selected.apellidos" disabled />
            </div>
            <div class="form-row">
              <label>Nombre</label>
              <input :value="selected.nombre" disabled />
            </div>
            <div class="form-row">
              <label>Correo</label>
              <input :value="medicoCorreo(selected)" disabled />
            </div>
            <div class="form-row">
              <label>Estado</label>
              <input :value="medicoEstado(selected)" disabled />
            </div>
            <div class="form-row full">
              <label for="plantilla-turno">Plantilla de turnos</label>
              <select id="plantilla-turno" v-model="selectedTemplate" required>
                <option v-for="option in turnoTemplateOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </div>
            <p class="message">Actual: {{ templateLabel(selected.plantilla_turno) }}</p>
          </div>
          <p v-if="message" class="message">{{ message }}</p>
          <p v-if="error" class="error">{{ error }}</p>
          <div class="actions-row">
            <button type="submit" :disabled="saving">{{ saving ? 'Guardando...' : 'Guardar' }}</button>
          </div>
        </template>
        <p v-else class="message">Seleccione un médico para asociar su plantilla de turnos.</p>
        <p v-if="!selected && error" class="error">{{ error }}</p>
      </form>
    </div>
  </section>
</template>
