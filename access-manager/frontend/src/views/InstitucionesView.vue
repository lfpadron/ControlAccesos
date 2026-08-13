<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import {
  activateInstitucion,
  createInstitucion,
  deactivateInstitucion,
  listComplejos,
  listConsultorios,
  listInstituciones,
  listPisos,
  listTorres,
  updateInstitucion,
  type Complejo,
  type Consultorio,
  type Institucion,
  type Piso,
  type Torre,
  type Usuario,
  type UsuarioRol,
} from '../api/client';
import LocationContextField from '../components/LocationContextField.vue';
import { useLocationContext } from '../composables/useLocationContext';
import { buildUserLocationScope, filterInstitucionesByUserAssignment, loadCurrentUserLocationAssignments } from '../locationAssignmentScope';

const instituciones = ref<Institucion[]>([]);
const complejos = ref<Complejo[]>([]);
const torres = ref<Torre[]>([]);
const pisos = ref<Piso[]>([]);
const consultorios = ref<Consultorio[]>([]);
const currentUser = ref<Usuario | null>(null);
const usuarioRoles = ref<UsuarioRol[]>([]);
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

const { clearLocation, setInstitution } = useLocationContext();

const userScope = computed(() =>
  buildUserLocationScope({
    currentUser: currentUser.value,
    usuarioRoles: usuarioRoles.value,
    instituciones: instituciones.value,
    complejos: complejos.value,
    torres: torres.value,
    pisos: pisos.value,
    consultorios: consultorios.value,
  }),
);

const filteredInstituciones = computed(() => {
  const term = filtro.value.trim().toLowerCase();
  const matchesQuery = term
    ? instituciones.value.filter((item) => `${item.nombre} ${item.razon_social ?? ''}`.toLowerCase().includes(term))
    : instituciones.value;
  return filterInstitucionesByUserAssignment(matchesQuery, userScope.value);
});

function setForm(item?: Institucion | null, syncLocation = true) {
  selected.value = item ?? null;
  form.nombre = item?.nombre ?? '';
  form.razon_social = item?.razon_social ?? '';
  form.notas = item?.notas ?? '';
  if (!syncLocation) return;
  if (item) {
    setInstitution({ id: item.id, label: item.nombre });
  } else {
    clearLocation();
  }
}

async function loadOptionalScopeCatalogs() {
  try {
    const [torresData, pisosData, consultoriosData] = await Promise.all([listTorres(), listPisos(), listConsultorios()]);
    return { torresData, pisosData, consultoriosData };
  } catch {
    return { torresData: [] as Torre[], pisosData: [] as Piso[], consultoriosData: [] as Consultorio[] };
  }
}

async function loadData() {
  loading.value = true;
  error.value = '';
  try {
    const [scopeData, institucionesData, complejosData, optionalScopeData] = await Promise.all([
      loadCurrentUserLocationAssignments(),
      listInstituciones(),
      listComplejos(),
      loadOptionalScopeCatalogs(),
    ]);
    currentUser.value = scopeData.currentUser;
    usuarioRoles.value = scopeData.usuarioRoles;
    instituciones.value = institucionesData;
    complejos.value = complejosData;
    torres.value = optionalScopeData.torresData;
    pisos.value = optionalScopeData.pisosData;
    consultorios.value = optionalScopeData.consultoriosData;
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
      const saved = await updateInstitucion(selected.value.id, payload);
      setInstitution({ id: saved.id, label: saved.nombre });
      message.value = 'Institución actualizada.';
    } else {
      await createInstitucion(payload);
      message.value = 'Institución creada.';
    }
    setForm(null, false);
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
    <LocationContextField />

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
                <th>Razón social</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in filteredInstituciones"
                :key="item.id"
                class="selectable-row"
                :class="{ selected: selected?.id === item.id }"
                @click="setForm(item)"
              >
                <td>{{ item.nombre }}</td>
                <td>{{ item.razon_social || 'Sin capturar' }}</td>
                <td><span class="status" :class="item.activo ? 'ok' : 'muted'">{{ item.activo ? 'Activa' : 'Inactiva' }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="filteredInstituciones.length === 0" class="message">No hay instituciones registradas.</p>
      </section>
    </div>
  </section>
</template>
