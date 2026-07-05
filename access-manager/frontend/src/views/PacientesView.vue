<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import {
  activatePaciente,
  createPaciente,
  deactivatePaciente,
  listPacientes,
  markPacienteForDeletion,
  searchPacientes,
  updatePaciente,
  type Paciente,
} from '../api/client';

const pacientes = ref<Paciente[]>([]);
const selected = ref<Paciente | null>(null);
const loading = ref(false);
const error = ref('');
const message = ref('');
const query = ref('');
const confirmPreferredOnly = ref(false);
const birthYearInput = ref<HTMLInputElement | null>(null);
const birthMonthInput = ref<HTMLInputElement | null>(null);
const birthDayInput = ref<HTMLInputElement | null>(null);

const form = reactive({
  nombre: '',
  nombre_preferido: '',
  apellido_paterno: '',
  apellido_materno: '',
  celular: '',
  fecha_nacimiento: '',
});

const birthDate = reactive({
  year: '',
  month: '',
  day: '',
});

const isPreferredOnly = computed(
  () =>
    Boolean(form.nombre_preferido.trim()) &&
    !form.nombre.trim() &&
    !form.apellido_paterno.trim() &&
    !form.apellido_materno.trim(),
);

function patientDisplayName(paciente: Paciente) {
  const legalName = [paciente.nombre, paciente.apellido_paterno, paciente.apellido_materno].filter(Boolean).join(' ');
  return paciente.nombre_preferido || legalName || 'Sin nombre';
}

function setBirthDateParts(value?: string | null) {
  const [year = '', month = '', day = ''] = value?.split('-') ?? [];
  birthDate.year = year;
  birthDate.month = month;
  birthDate.day = day;
  form.fecha_nacimiento = value ?? '';
}

function syncBirthDate() {
  if (!birthDate.year && !birthDate.month && !birthDate.day) {
    form.fecha_nacimiento = '';
    return;
  }
  if (birthDate.year.length !== 4 || birthDate.month.length !== 2 || birthDate.day.length !== 2) {
    form.fecha_nacimiento = '';
    return;
  }
  const isoDate = `${birthDate.year}-${birthDate.month}-${birthDate.day}`;
  const date = new Date(`${isoDate}T00:00:00`);
  const valid =
    !Number.isNaN(date.getTime()) &&
    date.getFullYear() === Number(birthDate.year) &&
    date.getMonth() + 1 === Number(birthDate.month) &&
    date.getDate() === Number(birthDate.day);
  form.fecha_nacimiento = valid ? isoDate : '';
}

function handleBirthDateInput(part: keyof typeof birthDate, maxLength: number, next?: 'month' | 'day') {
  birthDate[part] = birthDate[part].replace(/\D/g, '').slice(0, maxLength);
  syncBirthDate();
  if (birthDate[part].length === maxLength) {
    if (next === 'month') birthMonthInput.value?.focus();
    if (next === 'day') birthDayInput.value?.focus();
  }
}

function hasIncompleteBirthDate() {
  return Boolean(birthDate.year || birthDate.month || birthDate.day) && !form.fecha_nacimiento;
}

function trimOrNull(value: string) {
  const text = value.trim();
  return text || null;
}

function setForm(paciente?: Paciente | null) {
  selected.value = paciente ?? null;
  form.nombre = paciente?.nombre ?? '';
  form.nombre_preferido = paciente?.nombre_preferido ?? '';
  form.apellido_paterno = paciente?.apellido_paterno ?? '';
  form.apellido_materno = paciente?.apellido_materno ?? '';
  form.celular = paciente?.celular ?? '';
  setBirthDateParts(paciente?.fecha_nacimiento ?? '');
  confirmPreferredOnly.value = false;
}

async function load() {
  loading.value = true;
  error.value = '';
  try {
    pacientes.value = await listPacientes();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar pacientes.';
  } finally {
    loading.value = false;
  }
}

async function search() {
  if (!query.value.trim()) {
    await load();
    return;
  }
  loading.value = true;
  error.value = '';
  try {
    pacientes.value = await searchPacientes(query.value.trim());
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible buscar pacientes.';
  } finally {
    loading.value = false;
  }
}

async function submit(preferredOnlyConfirmed = false) {
  error.value = '';
  message.value = '';
  if (hasIncompleteBirthDate()) {
    error.value = 'Completa la fecha de nacimiento con año, mes y día válidos.';
    return;
  }
  if (!form.nombre_preferido.trim() && (!form.nombre.trim() || !form.apellido_paterno.trim())) {
    error.value = 'Captura nombre preferido o nombre y apellido paterno.';
    return;
  }
  if (isPreferredOnly.value && !preferredOnlyConfirmed) {
    confirmPreferredOnly.value = true;
    return;
  }
  confirmPreferredOnly.value = false;
  try {
    const payload = {
      nombre: trimOrNull(form.nombre),
      nombre_preferido: trimOrNull(form.nombre_preferido),
      apellido_paterno: trimOrNull(form.apellido_paterno),
      apellido_materno: trimOrNull(form.apellido_materno),
      celular: trimOrNull(form.celular),
      fecha_nacimiento: form.fecha_nacimiento || null,
    };
    if (selected.value) {
      await updatePaciente(selected.value.id, payload);
      message.value = 'Paciente actualizado.';
    } else {
      await createPaciente(payload);
      message.value = 'Paciente creado.';
    }
    setForm(null);
    await load();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible guardar el paciente.';
  }
}

async function setActive(active: boolean) {
  if (!selected.value) return;
  error.value = '';
  message.value = '';
  try {
    selected.value = active ? await activatePaciente(selected.value.id) : await deactivatePaciente(selected.value.id);
    message.value = active ? 'Paciente activado.' : 'Paciente desactivado.';
    await load();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cambiar el estado.';
  }
}

async function markForDeletion() {
  if (!selected.value) return;
  error.value = '';
  message.value = '';
  try {
    selected.value = await markPacienteForDeletion(selected.value.id);
    message.value = 'Paciente marcado para borrar.';
    await load();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible marcar para borrar.';
  }
}

onMounted(load);
</script>

<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1>Pacientes</h1>
        <p>Alta, búsqueda y control operativo sin datos clínicos.</p>
      </div>
    </div>

    <div class="grid catalog-grid">
      <form class="panel form compact-form" @submit.prevent="submit()">
        <h2>{{ selected ? 'Editar paciente' : 'Crear paciente' }}</h2>
        <div class="form-row">
          <label for="nombre">Nombre</label>
          <input id="nombre" v-model="form.nombre" :required="!form.nombre_preferido.trim()" maxlength="180" />
        </div>
        <div class="form-row">
          <label for="nombre_preferido">Nombre preferido</label>
          <input id="nombre_preferido" v-model="form.nombre_preferido" maxlength="60" @input="confirmPreferredOnly = false" />
        </div>
        <div class="form-row">
          <label for="apellido_paterno">Apellido paterno</label>
          <input id="apellido_paterno" v-model="form.apellido_paterno" :required="!form.nombre_preferido.trim()" maxlength="180" />
        </div>
        <div class="form-row">
          <label for="apellido_materno">Apellido materno</label>
          <input id="apellido_materno" v-model="form.apellido_materno" maxlength="180" />
        </div>
        <div class="form-row">
          <label for="celular">Celular</label>
          <input id="celular" v-model="form.celular" maxlength="40" />
        </div>
        <div class="form-row">
          <label for="fecha_nacimiento">Fecha de nacimiento</label>
          <div class="date-segments">
            <input
              id="fecha_nacimiento"
              ref="birthYearInput"
              v-model="birthDate.year"
              aria-label="Año de nacimiento"
              inputmode="numeric"
              maxlength="4"
              placeholder="AAAA"
              @input="handleBirthDateInput('year', 4, 'month')"
            />
            <input
              ref="birthMonthInput"
              v-model="birthDate.month"
              aria-label="Mes de nacimiento"
              inputmode="numeric"
              maxlength="2"
              placeholder="MM"
              @input="handleBirthDateInput('month', 2, 'day')"
            />
            <input
              ref="birthDayInput"
              v-model="birthDate.day"
              aria-label="Día de nacimiento"
              inputmode="numeric"
              maxlength="2"
              placeholder="DD"
              @input="handleBirthDateInput('day', 2)"
            />
          </div>
        </div>
        <div v-if="confirmPreferredOnly" class="duplicate-warning">
          <strong>Solo se capturó nombre preferido, ¿Continuar?</strong>
          <div class="actions-row">
            <button class="success" type="button" @click="submit(true)">Sí</button>
            <button class="danger solid" type="button" @click="confirmPreferredOnly = false">No</button>
          </div>
        </div>
        <div class="actions-row">
          <button type="submit">{{ selected ? 'Guardar cambios' : 'Crear paciente' }}</button>
          <button v-if="selected" class="secondary" type="button" @click="setForm(null)">Nuevo</button>
          <button v-if="selected?.activo" class="danger" type="button" @click="setActive(false)">Desactivar</button>
          <button v-else-if="selected" class="secondary" type="button" @click="setActive(true)">Activar</button>
          <button v-if="selected" class="danger" type="button" @click="markForDeletion">Marcar para borrar</button>
        </div>
        <p v-if="message" class="message">{{ message }}</p>
        <p v-if="error" class="error">{{ error }}</p>
      </form>

      <div class="panel table-panel">
        <div class="page-header compact">
          <h2>Listado</h2>
          <form class="inline-actions" @submit.prevent="search">
            <input v-model="query" placeholder="Nombre, celular o folio" />
            <button type="submit">Buscar</button>
            <button class="secondary" type="button" @click="query = ''; load()">Limpiar</button>
          </form>
        </div>
        <p v-if="loading" class="message">Cargando...</p>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Folio</th>
                <th>Paciente</th>
                <th>Nombre preferido</th>
                <th>Celular</th>
                <th>Estado</th>
                <th>Marcar borrar</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="paciente in pacientes"
                :key="paciente.id"
                class="selectable-row"
                :class="{ selected: selected?.id === paciente.id }"
                @click="setForm(paciente)"
              >
                <td>{{ paciente.folio_paciente }}</td>
                <td>{{ patientDisplayName(paciente) }}</td>
                <td>{{ paciente.nombre_preferido || '-' }}</td>
                <td>{{ paciente.celular || '-' }}</td>
                <td>
                  <span class="status" :class="paciente.activo ? 'ok' : 'muted'">
                    {{ paciente.activo ? 'Activo' : `Inactivo ${paciente.desactivado_en ? new Date(paciente.desactivado_en).toLocaleString() : ''}` }}
                  </span>
                </td>
                <td>{{ paciente.marcado_borrado_en ? new Date(paciente.marcado_borrado_en).toLocaleString() : '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>
</template>
