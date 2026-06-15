<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import {
  activateInstitucion,
  createInstitucion,
  deactivateInstitucion,
  listInstituciones,
  updateInstitucion,
  type Institucion,
} from '../api/client';

const instituciones = ref<Institucion[]>([]);
const selected = ref<Institucion | null>(null);
const error = ref('');
const message = ref('');
const loading = ref(false);
const filtro = ref('');

const form = reactive({
  nombre: '',
  razon_social: '',
  notas: '',
});

function setForm(item?: Institucion | null) {
  selected.value = item ?? null;
  form.nombre = item?.nombre ?? '';
  form.razon_social = item?.razon_social ?? '';
  form.notas = item?.notas ?? '';
}

async function loadData(q = filtro.value) {
  loading.value = true;
  error.value = '';
  try {
    instituciones.value = await listInstituciones(q.trim() || undefined);
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar instituciones.';
  } finally {
    loading.value = false;
  }
}

async function submit() {
  error.value = '';
  message.value = '';
  loading.value = true;
  try {
    const payload = {
      nombre: form.nombre,
      razon_social: form.razon_social || null,
      notas: form.notas || null,
    };
    if (selected.value) {
      await updateInstitucion(selected.value.id, payload);
      message.value = 'Institución actualizada.';
    } else {
      await createInstitucion(payload);
      message.value = 'Institución creada.';
    }
    setForm(null);
    await loadData();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible guardar la institución.';
  } finally {
    loading.value = false;
  }
}

async function setActive(active: boolean) {
  if (!selected.value) return;
  error.value = '';
  message.value = '';
  try {
    selected.value = active ? await activateInstitucion(selected.value.id) : await deactivateInstitucion(selected.value.id);
    message.value = active ? 'Institución activada.' : 'Institución desactivada.';
    await loadData();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cambiar el estado.';
  }
}

async function clearFilter() {
  filtro.value = '';
  await loadData('');
}

onMounted(() => loadData());
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Instituciones</h1>
        <p>Base para operar múltiples organizaciones desde una misma plataforma.</p>
      </div>
    </header>

    <section class="panel">
      <form class="inline-actions" @submit.prevent="loadData()">
        <input v-model="filtro" class="narrow-input" placeholder="Buscar por nombre o razón social" />
        <button type="submit">Buscar</button>
        <button class="secondary" type="button" @click="clearFilter">Limpiar</button>
      </form>
    </section>

    <div class="grid catalog-grid">
      <form class="panel form institution-form" @submit.prevent="submit">
        <h2>{{ selected ? 'Editar institución' : 'Crear institución' }}</h2>
        <div class="form-row">
          <label for="nombre">Nombre</label>
          <input id="nombre" v-model="form.nombre" required maxlength="120" />
        </div>
        <div class="form-row">
          <label for="razon">Razón social</label>
          <input id="razon" v-model="form.razon_social" maxlength="120" />
        </div>
        <div class="form-row">
          <label for="notas">Notas</label>
          <textarea id="notas" v-model="form.notas" maxlength="500" rows="4" />
        </div>
        <p v-if="message" class="message">{{ message }}</p>
        <p v-if="error" class="error">{{ error }}</p>
        <div class="actions-row">
          <button type="submit" :disabled="loading">{{ loading ? 'Guardando...' : '✓ Guardar' }}</button>
          <button class="danger solid" type="button" @click="setForm(null)">× Cancelar</button>
          <button v-if="selected?.activo" class="danger" type="button" @click="setActive(false)">Desactivar</button>
          <button v-else-if="selected" class="secondary" type="button" @click="setActive(true)">Activar</button>
        </div>
      </form>

      <section class="panel table-panel">
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in instituciones"
                :key="item.id"
                class="selectable-row"
                :class="{ selected: selected?.id === item.id }"
                @click="setForm(item)"
              >
                <td>{{ item.nombre }}</td>
                <td><span class="status" :class="item.activo ? 'ok' : 'muted'">{{ item.activo ? 'Activa' : 'Inactiva' }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="instituciones.length === 0" class="message">No hay instituciones registradas.</p>
      </section>
    </div>
  </section>
</template>
