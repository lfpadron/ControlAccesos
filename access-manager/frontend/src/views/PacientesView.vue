<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
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

const form = reactive({
  nombre: '',
  nombre_preferido: '',
  apellido_paterno: '',
  apellido_materno: '',
  celular: '',
  fecha_nacimiento: '',
});

function setForm(paciente?: Paciente | null) {
  selected.value = paciente ?? null;
  form.nombre = paciente?.nombre ?? '';
  form.nombre_preferido = paciente?.nombre_preferido ?? '';
  form.apellido_paterno = paciente?.apellido_paterno ?? '';
  form.apellido_materno = paciente?.apellido_materno ?? '';
  form.celular = paciente?.celular ?? '';
  form.fecha_nacimiento = paciente?.fecha_nacimiento ?? '';
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

async function submit() {
  error.value = '';
  message.value = '';
  try {
    const payload = {
      nombre: form.nombre,
      nombre_preferido: form.nombre_preferido || null,
      apellido_paterno: form.apellido_paterno,
      apellido_materno: form.apellido_materno || null,
      celular: form.celular || null,
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
      <form class="panel form compact-form" @submit.prevent="submit">
        <h2>{{ selected ? 'Editar paciente' : 'Crear paciente' }}</h2>
        <div class="form-row">
          <label for="nombre">Nombre</label>
          <input id="nombre" v-model="form.nombre" required maxlength="180" />
        </div>
        <div class="form-row">
          <label for="nombre_preferido">Nombre preferido</label>
          <input id="nombre_preferido" v-model="form.nombre_preferido" maxlength="60" />
        </div>
        <div class="form-row">
          <label for="apellido_paterno">Apellido paterno</label>
          <input id="apellido_paterno" v-model="form.apellido_paterno" required maxlength="180" />
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
          <input id="fecha_nacimiento" v-model="form.fecha_nacimiento" type="date" />
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
                <td>{{ paciente.nombre }} {{ paciente.apellido_paterno }} {{ paciente.apellido_materno || '' }}</td>
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
