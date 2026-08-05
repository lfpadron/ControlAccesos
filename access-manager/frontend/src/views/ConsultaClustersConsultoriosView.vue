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

const instituciones = ref<Institucion[]>([]);
const complejos = ref<Complejo[]>([]);
const torres = ref<Torre[]>([]);
const pisos = ref<Piso[]>([]);
const porConsultorio = ref<ConsultorioClusterConsulta[]>([]);
const porPiso = ref<PisoClusterConsulta[]>([]);
const loading = ref(false);
const error = ref('');

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

function clusterNames(item: ConsultorioClusterConsulta) {
  return item.clusters.length
    ? item.clusters.map((cluster) => `${cluster.nombre} (${cluster.activo ? 'Activo' : 'Inactivo'})`).join(', ')
    : 'Sin clúster';
}

function syncInstitution() {
  if (!scopedComplejos.value.some((item) => item.id === filters.complejo_id)) {
    filters.complejo_id = scopedComplejos.value[0]?.id ?? '';
  }
  syncComplex();
}

function syncComplex() {
  if (!scopedTorres.value.some((item) => item.id === filters.torre_id)) {
    filters.torre_id = scopedTorres.value[0]?.id ?? '';
  }
  syncTorre();
}

function syncTorre() {
  if (!scopedPisos.value.some((item) => item.id === filters.piso_id)) {
    filters.piso_id = '';
  }
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
    filters.institucion_id ||= instituciones.value[0]?.id ?? '';
    syncInstitution();
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

    <section class="panel">
      <div class="form-grid">
        <div class="form-row">
          <label for="consulta-institucion">Institución</label>
          <select id="consulta-institucion" v-model="filters.institucion_id" @change="syncInstitution(); consultar()">
            <option v-for="item in instituciones" :key="item.id" :value="item.id">{{ item.nombre }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="consulta-complejo">Complejo</label>
          <select id="consulta-complejo" v-model="filters.complejo_id" :disabled="!filters.institucion_id" @change="syncComplex(); consultar()">
            <option v-for="item in scopedComplejos" :key="item.id" :value="item.id">{{ item.nombre }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="consulta-torre">Torre</label>
          <select id="consulta-torre" v-model="filters.torre_id" :disabled="!filters.complejo_id" @change="syncTorre(); consultar()">
            <option v-for="item in scopedTorres" :key="item.id" :value="item.id">{{ item.nombre }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="consulta-piso">Piso</label>
          <select id="consulta-piso" v-model="filters.piso_id" :disabled="!filters.torre_id" @change="consultar">
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
