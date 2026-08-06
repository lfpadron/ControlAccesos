<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import {
  consultaClustersPorConsultorio,
  consultaClustersPorPiso,
  listComplejos,
  listInstituciones,
  listPisos,
  listTorres,
  type Complejo,
  type ConsultorioClusterConsulta,
  type Institucion,
  type Piso,
  type PisoClusterConsulta,
  type Torre,
} from '../api/client';
import LocationContextField from '../components/LocationContextField.vue';
import { useLocationContext } from '../composables/useLocationContext';

const instituciones = ref<Institucion[]>([]);
const complejos = ref<Complejo[]>([]);
const torres = ref<Torre[]>([]);
const pisos = ref<Piso[]>([]);
const porConsultorio = ref<ConsultorioClusterConsulta[]>([]);
const porPiso = ref<PisoClusterConsulta[]>([]);
const loading = ref(false);
const error = ref('');

const { clearFloor, clearLocation, locationContext, setCampus, setFloor, setInstitution, setTower } = useLocationContext();

const filters = reactive({
  institucion_id: '',
  complejo_id: '',
  torre_id: '',
  consultorio: '',
  sin_cluster: false,
  piso_id: '',
});

const scopedComplejos = computed(() =>
  filters.institucion_id ? complejos.value.filter((item) => item.institucion_id === filters.institucion_id) : [],
);
const scopedTorres = computed(() =>
  filters.complejo_id ? torres.value.filter((item) => item.complejo_id === filters.complejo_id) : [],
);
const scopedPisos = computed(() =>
  filters.torre_id ? pisos.value.filter((item) => item.torre_id === filters.torre_id) : [],
);

const selectedInstitution = computed(() => instituciones.value.find((item) => item.id === filters.institucion_id) ?? null);
const selectedCampus = computed(() => complejos.value.find((item) => item.id === filters.complejo_id) ?? null);
const selectedTower = computed(() => torres.value.find((item) => item.id === filters.torre_id) ?? null);
const selectedFloor = computed(() => pisos.value.find((item) => item.id === filters.piso_id) ?? null);

function clusterNames(item: ConsultorioClusterConsulta) {
  return item.clusters.length
    ? item.clusters.map((cluster) => `${cluster.nombre} (${cluster.activo ? 'Activo' : 'Inactivo'})`).join(', ')
    : 'Sin clúster';
}

function syncInstitution() {
  const institucion = selectedInstitution.value;
  if (!institucion) {
    clearLocation();
    filters.complejo_id = '';
    filters.torre_id = '';
    filters.piso_id = '';
    return;
  }
  setInstitution({ id: institucion.id, label: institucion.nombre });
  if (!scopedComplejos.value.some((item) => item.id === filters.complejo_id)) {
    filters.complejo_id = scopedComplejos.value[0]?.id ?? '';
  }
  syncComplex();
}

function syncComplex() {
  const campus = selectedCampus.value;
  if (!campus) {
    filters.torre_id = '';
    filters.piso_id = '';
    setInstitution(selectedInstitution.value ? { id: selectedInstitution.value.id, label: selectedInstitution.value.nombre } : null);
    return;
  }
  setCampus(
    { id: campus.id, label: campus.nombre },
    selectedInstitution.value ? { id: selectedInstitution.value.id, label: selectedInstitution.value.nombre } : undefined,
  );
  if (!scopedTorres.value.some((item) => item.id === filters.torre_id)) {
    filters.torre_id = scopedTorres.value[0]?.id ?? '';
  }
  syncTorre();
}

function syncTorre() {
  const torre = selectedTower.value;
  if (!torre) {
    filters.piso_id = '';
    setCampus(
      selectedCampus.value ? { id: selectedCampus.value.id, label: selectedCampus.value.nombre } : null,
      selectedInstitution.value ? { id: selectedInstitution.value.id, label: selectedInstitution.value.nombre } : undefined,
    );
    return;
  }
  setTower(
    { id: torre.id, label: torre.nombre },
    selectedCampus.value ? { id: selectedCampus.value.id, label: selectedCampus.value.nombre } : undefined,
    selectedInstitution.value ? { id: selectedInstitution.value.id, label: selectedInstitution.value.nombre } : undefined,
  );
  if (!scopedPisos.value.some((item) => item.id === filters.piso_id)) {
    filters.piso_id = '';
  }
}

function syncPiso() {
  if (!filters.piso_id) {
    clearFloor();
    return;
  }
  const piso = selectedFloor.value;
  if (!piso) {
    clearFloor();
    return;
  }
  setFloor(
    { id: piso.id, label: piso.nombre_visible },
    selectedTower.value ? { id: selectedTower.value.id, label: selectedTower.value.nombre } : undefined,
    selectedCampus.value ? { id: selectedCampus.value.id, label: selectedCampus.value.nombre } : undefined,
    selectedInstitution.value ? { id: selectedInstitution.value.id, label: selectedInstitution.value.nombre } : undefined,
  );
}

function applyLocationDefaults() {
  const contextInstitution = instituciones.value.find((item) => item.id === locationContext.institucion?.id);
  filters.institucion_id = contextInstitution?.id ?? instituciones.value[0]?.id ?? '';
  const contextCampus = scopedComplejos.value.find((item) => item.id === locationContext.campus?.id);
  filters.complejo_id = contextCampus?.id ?? scopedComplejos.value[0]?.id ?? '';
  const contextTower = scopedTorres.value.find((item) => item.id === locationContext.torre?.id);
  filters.torre_id = contextTower?.id ?? scopedTorres.value[0]?.id ?? '';
  const contextFloor = scopedPisos.value.find((item) => item.id === locationContext.piso?.id);
  filters.piso_id = contextFloor?.id ?? '';
  syncInstitution();
  syncPiso();
}

async function loadData() {
  loading.value = true;
  error.value = '';
  try {
    const [institucionesData, complejosData, torresData, pisosData] = await Promise.all([
      listInstituciones(),
      listComplejos(),
      listTorres(),
      listPisos(),
    ]);
    instituciones.value = institucionesData;
    complejos.value = complejosData;
    torres.value = torresData;
    pisos.value = pisosData;
    applyLocationDefaults();
    await consultar();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar la consulta.';
  } finally {
    loading.value = false;
  }
}

async function consultar() {
  if (!filters.torre_id) {
    porConsultorio.value = [];
    porPiso.value = [];
    return;
  }
  loading.value = true;
  error.value = '';
  try {
    const [consultorioData, pisoData] = await Promise.all([
      consultaClustersPorConsultorio({
        torre_id: filters.torre_id,
        q: filters.consultorio.trim() || undefined,
        sin_cluster: filters.sin_cluster,
      }),
      consultaClustersPorPiso({
        torre_id: filters.torre_id,
        piso_id: filters.piso_id || undefined,
      }),
    ]);
    porConsultorio.value = consultorioData;
    porPiso.value = pisoData;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible consultar clústers y consultorios.';
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
        <h1>Consulta de clústers y consultorios</h1>
        <p>Consulta operativa por torre, consultorio, nombre visible y piso.</p>
      </div>
      <button class="secondary" type="button" @click="loadData">Actualizar</button>
    </header>
    <LocationContextField />

    <section class="panel">
      <div class="form-grid">
        <div class="form-row">
          <label for="consulta-institucion">Institución</label>
          <select id="consulta-institucion" v-model="filters.institucion_id" @change="syncInstitution(); consultar()">
            <option value="">Seleccione institución</option>
            <option v-for="item in instituciones" :key="item.id" :value="item.id">{{ item.nombre }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="consulta-complejo">Campus</label>
          <select id="consulta-complejo" v-model="filters.complejo_id" :disabled="!filters.institucion_id" @change="syncComplex(); consultar()">
            <option value="">Seleccione campus</option>
            <option v-for="item in scopedComplejos" :key="item.id" :value="item.id">{{ item.nombre }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="consulta-torre">Torre</label>
          <select id="consulta-torre" v-model="filters.torre_id" :disabled="!filters.complejo_id" @change="syncTorre(); consultar()">
            <option value="">Seleccione torre</option>
            <option v-for="item in scopedTorres" :key="item.id" :value="item.id">{{ item.nombre }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="consulta-piso">Piso</label>
          <select id="consulta-piso" v-model="filters.piso_id" :disabled="!filters.torre_id" @change="syncPiso(); consultar()">
            <option value="">Todos los pisos</option>
            <option v-for="item in scopedPisos" :key="item.id" :value="item.id">{{ item.nombre_visible }}</option>
          </select>
        </div>
      </div>
      <div class="form-grid">
        <div class="form-row">
          <label for="consulta-consultorio">Consultorio o nombre visible</label>
          <input id="consulta-consultorio" v-model="filters.consultorio" @keyup.enter="consultar" />
        </div>
        <label class="check-row screen-active">
          <input v-model="filters.sin_cluster" type="checkbox" @change="consultar" />
          Mostrar consultorios sin clúster
        </label>
        <div class="actions-row screen-active">
          <button type="button" :disabled="loading || !filters.torre_id" @click="consultar">
            {{ loading ? 'Consultando...' : 'Consultar' }}
          </button>
        </div>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
    </section>

    <div class="grid catalog-grid">
      <section class="panel table-panel">
        <h2>Por consultorio</h2>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Consultorio</th>
                <th>Piso</th>
                <th>Clústers</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in porConsultorio" :key="item.id">
                <td>
                  <strong>{{ item.consultorio }}</strong>
                  <br />
                  <small>{{ item.codigo }}</small>
                </td>
                <td>{{ item.piso }}</td>
                <td>{{ clusterNames(item) }}</td>
                <td>{{ item.activo ? 'Activo' : 'Inactivo' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="!loading && porConsultorio.length === 0" class="message">No hay consultorios para mostrar.</p>
      </section>

      <section class="panel table-panel">
        <h2>Por piso</h2>
        <div class="turnos-preview">
          <article v-for="piso in porPiso" :key="piso.piso_id" class="turno-preview-item">
            <strong>{{ piso.piso }}</strong>
            <div>
              <div v-for="cluster in piso.clusters" :key="cluster.id">
                <b>{{ cluster.nombre }}</b>
                <span> · {{ cluster.activo ? 'Activo' : 'Inactivo' }}</span>
                <p class="message">
                  {{
                    cluster.consultorios.length
                      ? cluster.consultorios.map((item) => `${item.consultorio} (${item.activo ? 'Activo' : 'Inactivo'})`).join(', ')
                      : 'Sin consultorios asignados'
                  }}
                </p>
              </div>
              <p v-if="piso.consultorios_sin_cluster.length" class="warning">
                Sin clúster:
                {{ piso.consultorios_sin_cluster.map((item) => item.consultorio).join(', ') }}
              </p>
            </div>
            <small>{{ piso.clusters.length }} clúster(es)</small>
          </article>
        </div>
        <p v-if="!loading && porPiso.length === 0" class="message">No hay pisos para mostrar.</p>
      </section>
    </div>
  </section>
</template>
