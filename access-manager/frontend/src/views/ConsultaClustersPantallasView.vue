<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import {
  consultaClustersPantallas,
  listComplejos,
  listConsultorios,
  listInstituciones,
  listPisos,
  listTorres,
  type Complejo,
  type Consultorio,
  type Institucion,
  type PantallaClusterConsulta,
  type Piso,
  type Torre,
  type Usuario,
  type UsuarioRol,
} from '../api/client';
import LocationContextField from '../components/LocationContextField.vue';
import { useLocationContext } from '../composables/useLocationContext';
import { pisoTorreLabel, sortPisosByCodigo } from '../floorLabels';
import {
  buildUserLocationScope,
  filterComplejosByUserAssignment,
  filterInstitucionesByUserAssignment,
  filterTorresByUserAssignment,
  loadCurrentUserLocationAssignments,
} from '../locationAssignmentScope';

const instituciones = ref<Institucion[]>([]);
const complejos = ref<Complejo[]>([]);
const torres = ref<Torre[]>([]);
const pisos = ref<Piso[]>([]);
const consultorios = ref<Consultorio[]>([]);
const currentUser = ref<Usuario | null>(null);
const usuarioRoles = ref<UsuarioRol[]>([]);
const rows = ref<PantallaClusterConsulta[]>([]);
const loading = ref(false);
const error = ref('');
const hasSearched = ref(false);

const { clearFloor, clearLocation, setCampus, setFloor, setInstitution, setTower } = useLocationContext();

const filters = reactive({
  institucion_id: '',
  complejo_id: '',
  torre_id: '',
  piso_id: '',
  estado: 'todos',
  sin_cluster: false,
});

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

const visibleInstituciones = computed(() => filterInstitucionesByUserAssignment(instituciones.value, userScope.value));
const scopedComplejos = computed(() => {
  const base = filters.institucion_id ? complejos.value.filter((item) => item.institucion_id === filters.institucion_id) : [];
  return filterComplejosByUserAssignment(base, userScope.value);
});
const scopedTorres = computed(() => {
  const base = filters.complejo_id ? torres.value.filter((item) => item.complejo_id === filters.complejo_id) : [];
  return filterTorresByUserAssignment(base, userScope.value);
});
const scopedPisos = computed(() => (filters.torre_id ? sortPisosByCodigo(pisos.value.filter((item) => item.torre_id === filters.torre_id)) : []));

const selectedInstitution = computed(() => instituciones.value.find((item) => item.id === filters.institucion_id) ?? null);
const selectedCampus = computed(() => complejos.value.find((item) => item.id === filters.complejo_id) ?? null);
const selectedTower = computed(() => torres.value.find((item) => item.id === filters.torre_id) ?? null);
const selectedFloor = computed(() => pisos.value.find((item) => item.id === filters.piso_id) ?? null);

function pisoLabel(item: Piso) {
  return pisoTorreLabel(item, torres.value);
}

function syncInstitution() {
  const institucion = selectedInstitution.value;
  filters.complejo_id = scopedComplejos.value.some((item) => item.id === filters.complejo_id) ? filters.complejo_id : '';
  filters.torre_id = '';
  filters.piso_id = '';
  if (!institucion) {
    clearLocation();
    return;
  }
  setInstitution({ id: institucion.id, label: institucion.nombre });
}

function syncCampus() {
  const campus = selectedCampus.value;
  filters.torre_id = scopedTorres.value.some((item) => item.id === filters.torre_id) ? filters.torre_id : '';
  filters.piso_id = '';
  if (!campus) {
    if (selectedInstitution.value) {
      setInstitution({ id: selectedInstitution.value.id, label: selectedInstitution.value.nombre });
    } else {
      clearLocation();
    }
    return;
  }
  setCampus(
    { id: campus.id, label: campus.nombre },
    selectedInstitution.value ? { id: selectedInstitution.value.id, label: selectedInstitution.value.nombre } : undefined,
  );
}

function syncTower() {
  const torre = selectedTower.value;
  filters.piso_id = scopedPisos.value.some((item) => item.id === filters.piso_id) ? filters.piso_id : '';
  if (!torre) {
    syncCampus();
    return;
  }
  setTower(
    { id: torre.id, label: torre.nombre },
    selectedCampus.value ? { id: selectedCampus.value.id, label: selectedCampus.value.nombre } : undefined,
    selectedInstitution.value ? { id: selectedInstitution.value.id, label: selectedInstitution.value.nombre } : undefined,
  );
}

function syncFloor() {
  const piso = selectedFloor.value;
  if (!piso) {
    clearFloor();
    return;
  }
  setFloor(
    { id: piso.id, label: pisoLabel(piso) },
    selectedTower.value ? { id: selectedTower.value.id, label: selectedTower.value.nombre } : undefined,
    selectedCampus.value ? { id: selectedCampus.value.id, label: selectedCampus.value.nombre } : undefined,
    selectedInstitution.value ? { id: selectedInstitution.value.id, label: selectedInstitution.value.nombre } : undefined,
  );
}

function clusterNames(item: PantallaClusterConsulta) {
  if (item.clusters.length) {
    return item.clusters.map((cluster) => `${cluster.nombre} (${cluster.activo ? 'Activo' : 'Inactivo'})`).join(', ');
  }
  return item.cluster_ids.length ? 'Clúster no encontrado' : 'Sin clúster';
}

async function buscar() {
  loading.value = true;
  error.value = '';
  try {
    rows.value = await consultaClustersPantallas({
      institucion_id: filters.institucion_id || undefined,
      complejo_id: filters.complejo_id || undefined,
      torre_id: filters.torre_id || undefined,
      piso_id: filters.piso_id || undefined,
      estado: filters.estado,
      sin_cluster: filters.sin_cluster,
    });
    hasSearched.value = true;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible consultar clústers y pantallas.';
  } finally {
    loading.value = false;
  }
}

async function limpiar() {
  filters.institucion_id = '';
  filters.complejo_id = '';
  filters.torre_id = '';
  filters.piso_id = '';
  filters.estado = 'todos';
  filters.sin_cluster = false;
  clearLocation();
  await buscar();
}

async function loadData() {
  loading.value = true;
  error.value = '';
  try {
    const [scopeData, institucionesData, complejosData, torresData, pisosData, consultoriosData] = await Promise.all([
      loadCurrentUserLocationAssignments(),
      listInstituciones(),
      listComplejos(),
      listTorres(),
      listPisos(),
      listConsultorios(),
    ]);
    currentUser.value = scopeData.currentUser;
    usuarioRoles.value = scopeData.usuarioRoles;
    instituciones.value = institucionesData;
    complejos.value = complejosData;
    torres.value = torresData;
    pisos.value = pisosData;
    consultorios.value = consultoriosData;
    await buscar();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar la consulta.';
  } finally {
    loading.value = false;
  }
}

onMounted(loadData);
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Consulta de clúster y pantallas</h1>
        <p>Relación de pantallas de turnos con sus clústers asignados.</p>
      </div>
      <button class="secondary" type="button" @click="loadData">Actualizar</button>
    </header>
    <LocationContextField />

    <section class="panel form">
      <div class="form-grid">
        <div class="form-row">
          <label for="pantallas-institucion">Institución</label>
          <select id="pantallas-institucion" v-model="filters.institucion_id" @change="syncInstitution">
            <option value="">Todas</option>
            <option v-for="item in visibleInstituciones" :key="item.id" :value="item.id">{{ item.nombre }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="pantallas-campus">Campus</label>
          <select id="pantallas-campus" v-model="filters.complejo_id" :disabled="!filters.institucion_id" @change="syncCampus">
            <option value="">Todos</option>
            <option v-for="item in scopedComplejos" :key="item.id" :value="item.id">{{ item.nombre }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="pantallas-torre">Torre</label>
          <select id="pantallas-torre" v-model="filters.torre_id" :disabled="!filters.complejo_id" @change="syncTower">
            <option value="">Todas</option>
            <option v-for="item in scopedTorres" :key="item.id" :value="item.id">{{ item.nombre }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="pantallas-piso">Piso</label>
          <select id="pantallas-piso" v-model="filters.piso_id" :disabled="!filters.torre_id" @change="syncFloor">
            <option value="">Todos</option>
            <option v-for="item in scopedPisos" :key="item.id" :value="item.id">{{ pisoLabel(item) }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="pantallas-estado">Estado</label>
          <select id="pantallas-estado" v-model="filters.estado">
            <option value="todos">Todos</option>
            <option value="activa">Activas</option>
            <option value="inactiva">Inactivas</option>
          </select>
        </div>
      </div>
      <label class="check-row">
        <input v-model="filters.sin_cluster" type="checkbox" />
        Pantallas sin clúster asignado
      </label>
      <div class="actions-row">
        <button type="button" :disabled="loading" @click="buscar">{{ loading ? 'Buscando...' : 'Buscar' }}</button>
        <button class="secondary" type="button" :disabled="loading" @click="limpiar">Limpiar</button>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
    </section>

    <section class="panel table-panel">
      <div class="page-header compact">
        <div>
          <h2>{{ rows.length }} pantalla(s)</h2>
          <p>{{ filters.sin_cluster ? 'Sin clúster asignado' : 'Asignación de clústers' }}</p>
        </div>
      </div>
      <p v-if="loading" class="message">Cargando...</p>
      <div class="table-scroll devices-table">
        <table>
          <thead>
            <tr>
              <th>Dispositivo</th>
              <th>Nombre</th>
              <th>Institución</th>
              <th>Campus</th>
              <th>Torre</th>
              <th>Piso</th>
              <th>Clústers</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in rows" :key="item.id">
              <td>{{ item.codigo_dispositivo }}</td>
              <td>{{ item.nombre || '-' }}</td>
              <td>{{ item.institucion }}</td>
              <td>{{ item.campus }}</td>
              <td>{{ item.torre || '-' }}</td>
              <td>{{ item.piso || '-' }}</td>
              <td>{{ clusterNames(item) }}</td>
              <td>{{ item.activa ? 'Activa' : 'Inactiva' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="!loading && !hasSearched" class="message">Use Buscar para consultar pantallas.</p>
      <p v-else-if="!loading && rows.length === 0" class="message">No hay pantallas para mostrar.</p>
    </section>
  </section>
</template>
