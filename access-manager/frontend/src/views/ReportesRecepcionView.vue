<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import {
  listAccessibleInstituciones,
  listReporteRecepcionAgrupado,
  type Institucion,
  type ReporteRecepcionAgrupadoItem,
  type ReporteRecepcionHorarioItem,
} from '../api/client';
import { exportRows, type ExportColumn, type ExportFormat } from '../exporters';

type Grouping = 'mes' | 'semana' | 'dia' | 'hora';
type ReportRow = Record<string, string | number | null | undefined>;

const today = new Date().toISOString().slice(0, 10);
const currentMonth = today.slice(0, 7);
const currentWeek = isoWeekValue(new Date());
const hourLabels = Array.from({ length: 24 }, (_, hour) => `${String(hour).padStart(2, '0')}:00`);

const instituciones = ref<Institucion[]>([]);
const rows = ref<Array<ReporteRecepcionAgrupadoItem | ReporteRecepcionHorarioItem>>([]);
const loading = ref(false);
const error = ref('');
const filters = reactive({
  institucion_id: '',
  agrupacion: 'mes' as Grouping,
  mes_desde: currentMonth,
  mes_hasta: currentMonth,
  semana_desde: currentWeek,
  semana_hasta: currentWeek,
  dia_desde: today,
  dia_hasta: today,
  semana: currentWeek,
});

const isHourly = computed(() => rows.value.some((row) => 'horas' in row));
const tableRows = computed<ReportRow[]>(() => {
  if (isHourly.value) {
    return (rows.value as ReporteRecepcionHorarioItem[]).map((row) => ({
      campus: row.campus,
      torre: row.torre,
      piso: row.piso,
      fecha: row.fecha,
      dia_semana: row.dia_semana,
      ...row.horas,
      total: row.total,
    }));
  }
  return (rows.value as ReporteRecepcionAgrupadoItem[]).map((row) => ({
    campus: row.campus,
    torre: row.torre,
    piso: row.piso,
    periodo: row.periodo,
    citas: row.citas,
  }));
});

const columns = computed<ExportColumn<ReportRow>[]>(() => {
  const locationColumns = [
    { key: 'campus', label: 'Campus' },
    { key: 'torre', label: 'Torre' },
    { key: 'piso', label: 'Piso' },
  ];
  if (isHourly.value) {
    return [
      ...locationColumns,
      { key: 'fecha', label: 'Fecha' },
      { key: 'dia_semana', label: 'Día' },
      ...hourLabels.map((hour) => ({ key: hour, label: hour })),
      { key: 'total', label: 'Total' },
    ];
  }
  return [
    ...locationColumns,
    { key: 'periodo', label: 'Periodo' },
    { key: 'citas', label: 'Citas' },
  ];
});

function isoWeekValue(value: Date) {
  const date = new Date(Date.UTC(value.getFullYear(), value.getMonth(), value.getDate()));
  const day = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  const week = Math.ceil(((date.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  return `${date.getUTCFullYear()}-W${String(week).padStart(2, '0')}`;
}

async function loadInstituciones() {
  instituciones.value = await listAccessibleInstituciones();
  if (instituciones.value.length === 1) {
    filters.institucion_id = instituciones.value[0].id;
  }
}

async function filterRows() {
  if (!filters.institucion_id) {
    rows.value = [];
    return;
  }
  loading.value = true;
  error.value = '';
  try {
    rows.value = await listReporteRecepcionAgrupado(filters);
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar el reporte.';
  } finally {
    loading.value = false;
  }
}

function clearFilters() {
  filters.institucion_id = instituciones.value.length === 1 ? instituciones.value[0].id : '';
  filters.agrupacion = 'mes';
  filters.mes_desde = currentMonth;
  filters.mes_hasta = currentMonth;
  filters.semana_desde = currentWeek;
  filters.semana_hasta = currentWeek;
  filters.dia_desde = today;
  filters.dia_hasta = today;
  filters.semana = currentWeek;
  rows.value = [];
}

function exportReport(format: ExportFormat) {
  exportRows(tableRows.value, columns.value, 'reporte-recepcion-citas', format);
}

watch(
  () => filters.institucion_id,
  () => {
    if (filters.institucion_id) {
      void filterRows();
    }
  },
);

onMounted(async () => {
  try {
    await loadInstituciones();
    await filterRows();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar instituciones.';
  }
});
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Reportes recepción</h1>
        <p>Citas por campus, torre y piso.</p>
      </div>
    </header>

    <section class="panel form">
      <div class="form-grid">
        <div class="form-row">
          <label for="rep-rec-institucion">Institución</label>
          <select id="rep-rec-institucion" v-model="filters.institucion_id" required>
            <option value="">Seleccione institución</option>
            <option v-for="institucion in instituciones" :key="institucion.id" :value="institucion.id">{{ institucion.nombre }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="rep-rec-agrupacion">Agrupación</label>
          <select id="rep-rec-agrupacion" v-model="filters.agrupacion">
            <option value="mes">Mes</option>
            <option value="semana">Semana</option>
            <option value="dia">Días</option>
            <option value="hora">Hora</option>
          </select>
        </div>
        <template v-if="filters.agrupacion === 'mes'">
          <div class="form-row">
            <label for="rep-rec-mes-desde">Mes desde</label>
            <input id="rep-rec-mes-desde" v-model="filters.mes_desde" type="month" />
          </div>
          <div class="form-row">
            <label for="rep-rec-mes-hasta">Mes hasta</label>
            <input id="rep-rec-mes-hasta" v-model="filters.mes_hasta" type="month" />
          </div>
        </template>
        <template v-else-if="filters.agrupacion === 'semana'">
          <div class="form-row">
            <label for="rep-rec-semana-desde">Semana desde</label>
            <input id="rep-rec-semana-desde" v-model="filters.semana_desde" type="week" />
          </div>
          <div class="form-row">
            <label for="rep-rec-semana-hasta">Semana hasta</label>
            <input id="rep-rec-semana-hasta" v-model="filters.semana_hasta" type="week" />
          </div>
        </template>
        <template v-else-if="filters.agrupacion === 'hora'">
          <div class="form-row">
            <label for="rep-rec-semana">Semana</label>
            <input id="rep-rec-semana" v-model="filters.semana" type="week" />
          </div>
        </template>
        <template v-else>
          <div class="form-row">
            <label for="rep-rec-dia-desde">Día desde</label>
            <input id="rep-rec-dia-desde" v-model="filters.dia_desde" type="date" />
          </div>
          <div class="form-row">
            <label for="rep-rec-dia-hasta">Día hasta</label>
            <input id="rep-rec-dia-hasta" v-model="filters.dia_hasta" type="date" />
          </div>
        </template>
      </div>

      <div class="actions-row">
        <button type="button" :disabled="loading || !filters.institucion_id" @click="filterRows">Filtrar</button>
        <button class="secondary" type="button" @click="clearFilters">Limpiar</button>
        <button class="secondary" type="button" @click="exportReport('excel')">Excel</button>
        <button class="secondary" type="button" @click="exportReport('pdf')">PDF</button>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
    </section>

    <section class="panel table-panel">
      <p v-if="loading" class="message">Cargando...</p>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th v-for="column in columns" :key="String(column.key)">{{ column.label }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in tableRows" :key="index">
              <td v-for="column in columns" :key="String(column.key)">{{ row[String(column.key)] ?? 0 }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="!loading && tableRows.length === 0" class="message">No hay registros para mostrar.</p>
    </section>
  </section>
</template>
