<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import {
  listComplejos,
  listConsultorios,
  listClustersTurnos,
  listInstituciones,
  listPantallasTurnos,
  listPisos,
  listSalasEspera,
  type ClusterTurnos,
  type Complejo,
  type Consultorio,
  type Institucion,
  type PantallaTurnos,
  type Piso,
  type SalaEspera,
} from '../api/client';
import { exportRows, type ExportFormat } from '../exporters';

type Level = 'instituciones' | 'complejos' | 'pisos' | 'consultorios' | 'salas' | 'clusters-pantallas';
type ActiveFilter = 'todos' | 'activos' | 'inactivos';
type ReportRow = Record<string, string | boolean | null>;

const levelOptions: Array<{ value: Level; label: string }> = [
  { value: 'instituciones', label: 'Instituciones' },
  { value: 'complejos', label: 'Complejos' },
  { value: 'pisos', label: 'Pisos' },
  { value: 'consultorios', label: 'Consultorios' },
  { value: 'salas', label: 'Salas de espera' },
  { value: 'clusters-pantallas', label: 'Clústers y pantallas' },
];

const level = ref<Level>('instituciones');
const activeFilter = ref<ActiveFilter>('todos');
const instituciones = ref<Institucion[]>([]);
const complejos = ref<Complejo[]>([]);
const pisos = ref<Piso[]>([]);
const consultorios = ref<Consultorio[]>([]);
const salas = ref<SalaEspera[]>([]);
const clusters = ref<ClusterTurnos[]>([]);
const pantallas = ref<PantallaTurnos[]>([]);
const institucionSearch = ref('');
const complejoSearch = ref('');
const pisoSearch = ref('');
const error = ref('');
const loading = ref(false);
const selectedInstitucionId = ref('');
const selectedComplejoId = ref('');
const selectedPisoId = ref('');

const filteredComplejos = computed(() =>
  selectedInstitucionId.value ? complejos.value.filter((item) => item.institucion_id === selectedInstitucionId.value) : complejos.value,
);

const filteredPisos = computed(() =>
  selectedComplejoId.value ? pisos.value.filter((item) => item.complejo_id === selectedComplejoId.value) : pisos.value,
);

function institucionLabel(item: Institucion) {
  return item.razon_social ? `${item.nombre} · ${item.razon_social}` : item.nombre;
}

function matchByLabel<T>(rows: T[], text: string, labeler: (item: T) => string) {
  const normalized = text.trim().toLowerCase();
  return rows.find((item) => {
    const label = labeler(item).toLowerCase();
    return label === normalized || label.split(' · ')[0] === normalized;
  });
}

function syncInstitution() {
  selectedInstitucionId.value = matchByLabel(instituciones.value, institucionSearch.value, institucionLabel)?.id ?? '';
  if (!filteredComplejos.value.some((item) => item.id === selectedComplejoId.value)) {
    selectedComplejoId.value = '';
    complejoSearch.value = '';
    selectedPisoId.value = '';
    pisoSearch.value = '';
  }
}

function syncComplex() {
  selectedComplejoId.value = matchByLabel(filteredComplejos.value, complejoSearch.value, (item) => item.nombre)?.id ?? '';
  if (!filteredPisos.value.some((item) => item.id === selectedPisoId.value)) {
    selectedPisoId.value = '';
    pisoSearch.value = '';
  }
}

function syncPiso() {
  selectedPisoId.value = matchByLabel(filteredPisos.value, pisoSearch.value, (item) => item.nombre_visible)?.id ?? '';
}

function statusText(active: boolean) {
  return active ? 'Activo' : 'Inactivo';
}

function passesActive(active: boolean) {
  if (activeFilter.value === 'todos') return true;
  return activeFilter.value === 'activos' ? active : !active;
}

function complejoName(id: string | null | undefined) {
  return complejos.value.find((item) => item.id === id)?.nombre ?? '';
}

function institucionName(id: string | null | undefined) {
  return instituciones.value.find((item) => item.id === id)?.nombre ?? '';
}

function pisoName(id: string | null | undefined) {
  return pisos.value.find((item) => item.id === id)?.nombre_visible ?? '';
}

function inScope(row: { complejo_id?: string | null; piso_id?: string | null }) {
  if (selectedComplejoId.value && row.complejo_id !== selectedComplejoId.value) return false;
  if (selectedPisoId.value && row.piso_id !== selectedPisoId.value) return false;
  if (!selectedInstitucionId.value) return true;
  const complejo = complejos.value.find((item) => item.id === row.complejo_id);
  return complejo?.institucion_id === selectedInstitucionId.value;
}

const rows = computed<ReportRow[]>(() => {
  if (level.value === 'instituciones') {
    return instituciones.value
      .filter((item) => passesActive(item.activo))
      .map((item) => ({
        tipo: 'Institución',
        institucion: item.nombre,
        complejo: '',
        piso: '',
        nombre: item.razon_social || item.nombre,
        estado: statusText(item.activo),
      }));
  }
  if (level.value === 'complejos') {
    return filteredComplejos.value
      .filter((item) => passesActive(item.activo))
      .map((item) => ({
        tipo: 'Complejo',
        institucion: institucionName(item.institucion_id),
        complejo: item.nombre,
        piso: '',
        nombre: item.direccion || item.nombre,
        estado: statusText(item.activo),
      }));
  }
  if (level.value === 'pisos') {
    return filteredPisos.value
      .filter((item) => inScope(item) && passesActive(item.activo))
      .map((item) => ({
        tipo: 'Piso',
        institucion: institucionName(complejos.value.find((complex) => complex.id === item.complejo_id)?.institucion_id),
        complejo: complejoName(item.complejo_id),
        piso: item.nombre_visible,
        nombre: item.numero,
        estado: statusText(item.activo),
      }));
  }
  if (level.value === 'consultorios') {
    return consultorios.value
      .filter((item) => inScope(item) && passesActive(item.activo))
      .map((item) => ({
        tipo: 'Consultorio',
        institucion: institucionName(complejos.value.find((complex) => complex.id === item.complejo_id)?.institucion_id),
        complejo: complejoName(item.complejo_id),
        piso: pisoName(item.piso_id),
        nombre: item.nombre_visible || item.codigo,
        estado: statusText(item.activo),
      }));
  }
  if (level.value === 'salas') {
    return salas.value
      .filter((item) => inScope(item) && passesActive(item.activa))
      .map((item) => ({
        tipo: 'Sala de espera',
        institucion: institucionName(complejos.value.find((complex) => complex.id === item.complejo_id)?.institucion_id),
        complejo: complejoName(item.complejo_id),
        piso: pisoName(item.piso_id),
        nombre: item.nombre,
        estado: statusText(item.activa),
      }));
  }
  const clusterRows = clusters.value
    .filter((item) => inScope(item) && passesActive(item.activo))
    .map((item) => ({
      tipo: 'Clúster',
      institucion: institucionName(complejos.value.find((complex) => complex.id === item.complejo_id)?.institucion_id),
      complejo: complejoName(item.complejo_id),
      piso: pisoName(item.piso_id),
      nombre: item.nombre,
      estado: statusText(item.activo),
    }));
  const screenRows = pantallas.value
    .filter((item) => inScope(item) && passesActive(item.activa))
    .map((item) => ({
      tipo: 'Pantalla',
      institucion: institucionName(complejos.value.find((complex) => complex.id === item.complejo_id)?.institucion_id),
      complejo: complejoName(item.complejo_id),
      piso: pisoName(item.piso_id),
      nombre: item.nombre || item.codigo_dispositivo,
      estado: statusText(item.activa),
    }));
  return [...clusterRows, ...screenRows];
});

const columns = [
  { key: 'tipo', label: 'Tipo' },
  { key: 'institucion', label: 'Institución' },
  { key: 'complejo', label: 'Complejo' },
  { key: 'piso', label: 'Piso' },
  { key: 'nombre', label: 'Nombre' },
  { key: 'estado', label: 'Estado' },
];

async function loadData() {
  loading.value = true;
  error.value = '';
  try {
    const [institucionesData, complejosData, pisosData, consultoriosData, salasData, clustersData, pantallasData] = await Promise.all([
      listInstituciones(),
      listComplejos(),
      listPisos(),
      listConsultorios(),
      listSalasEspera(),
      listClustersTurnos(),
      listPantallasTurnos(),
    ]);
    instituciones.value = institucionesData;
    complejos.value = complejosData;
    pisos.value = pisosData;
    consultorios.value = consultoriosData;
    salas.value = salasData;
    clusters.value = clustersData;
    pantallas.value = pantallasData;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar reportes.';
  } finally {
    loading.value = false;
  }
}

function clearFilters() {
  selectedInstitucionId.value = '';
  selectedComplejoId.value = '';
  selectedPisoId.value = '';
  institucionSearch.value = '';
  complejoSearch.value = '';
  pisoSearch.value = '';
  activeFilter.value = 'todos';
}

function exportReport(format: ExportFormat) {
  exportRows(rows.value, columns, `reporte-${level.value}`, format);
}

onMounted(loadData);
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Reportes</h1>
        <p>Inventario jerárquico por institución, complejo, piso y áreas operativas.</p>
      </div>
      <button class="secondary" type="button" @click="loadData">Actualizar</button>
    </header>

    <section class="panel form">
      <div class="segmented-actions">
        <button
          v-for="option in levelOptions"
          :key="option.value"
          class="secondary"
          :class="{ selected: level === option.value }"
          type="button"
          @click="level = option.value"
        >
          {{ option.label }}
        </button>
      </div>

      <div class="form-grid">
        <div class="form-row">
          <label for="reporte-institucion">Institución</label>
          <input id="reporte-institucion" v-model="institucionSearch" list="reporte-instituciones" @input="syncInstitution" @change="syncInstitution" />
          <datalist id="reporte-instituciones">
            <option v-for="item in instituciones" :key="item.id" :value="institucionLabel(item)" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="reporte-complejo">Complejo</label>
          <input
            id="reporte-complejo"
            v-model="complejoSearch"
            list="reporte-complejos"
            :disabled="level === 'instituciones'"
            @input="syncComplex"
            @change="syncComplex"
          />
          <datalist id="reporte-complejos">
            <option v-for="item in filteredComplejos" :key="item.id" :value="item.nombre" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="reporte-piso">Piso</label>
          <input
            id="reporte-piso"
            v-model="pisoSearch"
            list="reporte-pisos"
            :disabled="level === 'instituciones' || level === 'complejos'"
            @input="syncPiso"
            @change="syncPiso"
          />
          <datalist id="reporte-pisos">
            <option v-for="item in filteredPisos" :key="item.id" :value="item.nombre_visible" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="reporte-activo">Estado</label>
          <select id="reporte-activo" v-model="activeFilter">
            <option value="todos">Todos</option>
            <option value="activos">Activos</option>
            <option value="inactivos">Inactivos</option>
          </select>
        </div>
      </div>

      <div class="actions-row">
        <button class="secondary" type="button" @click="clearFilters">Limpiar</button>
        <button class="secondary" type="button" @click="exportReport('excel')">Excel</button>
        <button class="secondary" type="button" @click="exportReport('csv')">CSV</button>
        <button class="secondary" type="button" @click="exportReport('json')">JSON</button>
      </div>
    </section>

    <section class="panel table-panel">
      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="loading" class="message">Cargando...</p>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th v-for="column in columns" :key="column.key">{{ column.label }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in rows" :key="`${row.tipo}-${row.nombre}-${index}`">
              <td v-for="column in columns" :key="column.key">{{ row[column.key] || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="!loading && rows.length === 0" class="message">No hay registros para mostrar.</p>
    </section>
  </section>
</template>
