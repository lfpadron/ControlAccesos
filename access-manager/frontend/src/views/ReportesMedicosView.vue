<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import {
  listAccessibleMedicos,
  listReporteMedicoAgrupado,
  listReporteMedicoCitas,
  listReporteMedicoPacientes,
  type Medico,
  type ReporteAgrupadoItem,
  type ReporteCitaItem,
  type ReporteHorarioItem,
  type ReportePacienteItem,
} from '../api/client';
import { exportRows, type ExportColumn, type ExportFormat } from '../exporters';

type Tab = 'pacientes' | 'citas' | 'agrupado';
type Grouping = 'mes' | 'semana' | 'dia' | 'hora';
type ReportRow = Record<string, string | number | boolean | null | undefined>;

const today = new Date().toISOString().slice(0, 10);
const currentMonth = today.slice(0, 7);
const currentWeek = isoWeekValue(new Date());
const hourLabels = Array.from({ length: 24 }, (_, hour) => `${String(hour).padStart(2, '0')}:00`);

const tab = ref<Tab>('pacientes');
const medicos = ref<Medico[]>([]);
const pacientes = ref<ReportePacienteItem[]>([]);
const citas = ref<ReporteCitaItem[]>([]);
const agrupado = ref<Array<ReporteAgrupadoItem | ReporteHorarioItem>>([]);
const loading = ref(false);
const error = ref('');

const patientFilters = reactive({
  medico_id: '',
  paciente: '',
});
const citaFilters = reactive({
  fecha_desde: today,
  fecha_hasta: today,
});
const groupFilters = reactive({
  agrupacion: 'mes' as Grouping,
  mes_desde: currentMonth,
  mes_hasta: currentMonth,
  semana_desde: currentWeek,
  semana_hasta: currentWeek,
  dia_desde: today,
  dia_hasta: today,
  semana: currentWeek,
});

const groupedIsHourly = computed(() => agrupado.value.some((row) => 'horas' in row));

function isoWeekValue(value: Date) {
  const date = new Date(Date.UTC(value.getFullYear(), value.getMonth(), value.getDate()));
  const day = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  const week = Math.ceil(((date.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  return `${date.getUTCFullYear()}-W${String(week).padStart(2, '0')}`;
}

function medicoLabel(item: Medico) {
  return item.nombre_visible || `${item.apellidos}, ${item.nombre}`.replace(/^, |, $/g, '');
}

function presented(value: boolean | null | undefined) {
  if (value === null || value === undefined) return '-';
  return value ? 'Sí' : 'No';
}

function shortTime(value: string | null | undefined) {
  return value ? value.slice(0, 5) : '-';
}

function groupedRows(): ReportRow[] {
  if (groupedIsHourly.value) {
    return (agrupado.value as ReporteHorarioItem[]).map((row) => ({
      fecha: row.fecha,
      dia_semana: row.dia_semana,
      ...row.horas,
      total: row.total,
    }));
  }
  return (agrupado.value as ReporteAgrupadoItem[]).map((row) => ({
    periodo: row.periodo,
    citas: row.citas,
  }));
}

const patientColumns: ExportColumn<ReportePacienteItem>[] = [
  { key: 'folio_paciente', label: 'Folio' },
  { key: 'paciente', label: 'Paciente' },
  { key: 'medico', label: 'Médico' },
  { key: 'fecha_ultima_cita', label: 'Última cita' },
  { key: 'hora_ultima_cita', label: 'Hora', value: (row) => shortTime(row.hora_ultima_cita) },
  { key: 'se_presento', label: 'Se presentó', value: (row) => presented(row.se_presento) },
];

const citaColumns: ExportColumn<ReporteCitaItem>[] = [
  { key: 'fecha_cita', label: 'Fecha' },
  { key: 'hora_cita', label: 'Hora', value: (row) => shortTime(row.hora_cita) },
  { key: 'paciente', label: 'Paciente' },
  { key: 'medico', label: 'Médico' },
  { key: 'campus', label: 'Campus' },
  { key: 'torre', label: 'Torre' },
  { key: 'piso', label: 'Piso' },
  { key: 'consultorio', label: 'Consultorio' },
  { key: 'se_presento', label: 'Se presentó', value: (row) => presented(row.se_presento) },
];

const groupedColumns = computed<ExportColumn<ReportRow>[]>(() => {
  if (groupedIsHourly.value) {
    return [
      { key: 'fecha', label: 'Fecha' },
      { key: 'dia_semana', label: 'Día' },
      ...hourLabels.map((hour) => ({ key: hour, label: hour })),
      { key: 'total', label: 'Total' },
    ];
  }
  return [
    { key: 'periodo', label: 'Periodo' },
    { key: 'citas', label: 'Citas' },
  ];
});

async function loadMedicos() {
  medicos.value = await listAccessibleMedicos();
}

async function filterPatients() {
  loading.value = true;
  error.value = '';
  try {
    pacientes.value = await listReporteMedicoPacientes(patientFilters);
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar pacientes.';
  } finally {
    loading.value = false;
  }
}

async function filterCitas() {
  loading.value = true;
  error.value = '';
  try {
    citas.value = await listReporteMedicoCitas(citaFilters);
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar citas.';
  } finally {
    loading.value = false;
  }
}

async function filterGrouped() {
  loading.value = true;
  error.value = '';
  try {
    agrupado.value = await listReporteMedicoAgrupado(groupFilters);
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar el reporte agrupado.';
  } finally {
    loading.value = false;
  }
}

function clearPatients() {
  patientFilters.medico_id = '';
  patientFilters.paciente = '';
  pacientes.value = [];
}

function clearCitas() {
  citaFilters.fecha_desde = today;
  citaFilters.fecha_hasta = today;
  citas.value = [];
}

function clearGrouped() {
  groupFilters.agrupacion = 'mes';
  groupFilters.mes_desde = currentMonth;
  groupFilters.mes_hasta = currentMonth;
  groupFilters.semana_desde = currentWeek;
  groupFilters.semana_hasta = currentWeek;
  groupFilters.dia_desde = today;
  groupFilters.dia_hasta = today;
  groupFilters.semana = currentWeek;
  agrupado.value = [];
}

function exportPatients(format: ExportFormat) {
  exportRows(pacientes.value, patientColumns, 'reporte-medico-pacientes', format);
}

function exportCitas(format: ExportFormat) {
  exportRows(citas.value, citaColumns, 'reporte-medico-citas', format);
}

function exportGrouped(format: ExportFormat) {
  exportRows(groupedRows(), groupedColumns.value, 'reporte-medico-citas-agrupadas', format);
}

onMounted(async () => {
  try {
    await loadMedicos();
    await filterPatients();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar catálogos.';
  }
});
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Reportes médicos</h1>
        <p>Pacientes, citas y conteos de agenda.</p>
      </div>
    </header>

    <section class="panel form">
      <div class="segmented-actions">
        <button class="secondary" :class="{ selected: tab === 'pacientes' }" type="button" @click="tab = 'pacientes'">Pacientes</button>
        <button class="secondary" :class="{ selected: tab === 'citas' }" type="button" @click="tab = 'citas'">Citas</button>
        <button class="secondary" :class="{ selected: tab === 'agrupado' }" type="button" @click="tab = 'agrupado'">Número de citas</button>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
    </section>

    <section v-if="tab === 'pacientes'" class="panel form">
      <div class="form-grid">
        <div class="form-row">
          <label for="rep-medico">Médico</label>
          <select id="rep-medico" v-model="patientFilters.medico_id">
            <option value="">Todos</option>
            <option v-for="medico in medicos" :key="medico.id" :value="medico.id">{{ medicoLabel(medico) }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="rep-paciente">Paciente</label>
          <input id="rep-paciente" v-model="patientFilters.paciente" @keyup.enter="filterPatients" />
        </div>
      </div>
      <div class="actions-row">
        <button type="button" :disabled="loading" @click="filterPatients">Filtrar</button>
        <button class="secondary" type="button" @click="clearPatients">Limpiar</button>
        <button class="secondary" type="button" @click="exportPatients('excel')">Excel</button>
        <button class="secondary" type="button" @click="exportPatients('pdf')">PDF</button>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Folio</th>
              <th>Paciente</th>
              <th>Médico</th>
              <th>Última cita</th>
              <th>Se presentó</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in pacientes" :key="row.paciente_id">
              <td>{{ row.folio_paciente }}</td>
              <td>{{ row.paciente }}</td>
              <td>{{ row.medico || '-' }}</td>
              <td>{{ row.fecha_ultima_cita || '-' }}</td>
              <td>{{ presented(row.se_presento) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="tab === 'citas'" class="panel form">
      <div class="form-grid">
        <div class="form-row">
          <label for="rep-citas-desde">Fecha desde</label>
          <input id="rep-citas-desde" v-model="citaFilters.fecha_desde" type="date" />
        </div>
        <div class="form-row">
          <label for="rep-citas-hasta">Fecha hasta</label>
          <input id="rep-citas-hasta" v-model="citaFilters.fecha_hasta" type="date" />
        </div>
      </div>
      <div class="actions-row">
        <button type="button" :disabled="loading" @click="filterCitas">Filtrar</button>
        <button class="secondary" type="button" @click="clearCitas">Limpiar</button>
        <button class="secondary" type="button" @click="exportCitas('excel')">Excel</button>
        <button class="secondary" type="button" @click="exportCitas('pdf')">PDF</button>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Hora</th>
              <th>Paciente</th>
              <th>Médico</th>
              <th>Consultorio</th>
              <th>Se presentó</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in citas" :key="row.cita_id">
              <td>{{ row.fecha_cita }}</td>
              <td>{{ shortTime(row.hora_cita) }}</td>
              <td>{{ row.paciente }}</td>
              <td>{{ row.medico }}</td>
              <td>{{ [row.campus, row.torre, row.piso, row.consultorio].filter(Boolean).join(' · ') }}</td>
              <td>{{ presented(row.se_presento) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="tab === 'agrupado'" class="panel form">
      <div class="form-grid">
        <div class="form-row">
          <label for="rep-agrupacion">Agrupación</label>
          <select id="rep-agrupacion" v-model="groupFilters.agrupacion">
            <option value="mes">Mes</option>
            <option value="semana">Semana</option>
            <option value="dia">Días</option>
            <option value="hora">Hora</option>
          </select>
        </div>
        <template v-if="groupFilters.agrupacion === 'mes'">
          <div class="form-row">
            <label for="rep-mes-desde">Mes desde</label>
            <input id="rep-mes-desde" v-model="groupFilters.mes_desde" type="month" />
          </div>
          <div class="form-row">
            <label for="rep-mes-hasta">Mes hasta</label>
            <input id="rep-mes-hasta" v-model="groupFilters.mes_hasta" type="month" />
          </div>
        </template>
        <template v-else-if="groupFilters.agrupacion === 'semana'">
          <div class="form-row">
            <label for="rep-semana-desde">Semana desde</label>
            <input id="rep-semana-desde" v-model="groupFilters.semana_desde" type="week" />
          </div>
          <div class="form-row">
            <label for="rep-semana-hasta">Semana hasta</label>
            <input id="rep-semana-hasta" v-model="groupFilters.semana_hasta" type="week" />
          </div>
        </template>
        <template v-else-if="groupFilters.agrupacion === 'hora'">
          <div class="form-row">
            <label for="rep-semana">Semana</label>
            <input id="rep-semana" v-model="groupFilters.semana" type="week" />
          </div>
        </template>
        <template v-else>
          <div class="form-row">
            <label for="rep-dia-desde">Día desde</label>
            <input id="rep-dia-desde" v-model="groupFilters.dia_desde" type="date" />
          </div>
          <div class="form-row">
            <label for="rep-dia-hasta">Día hasta</label>
            <input id="rep-dia-hasta" v-model="groupFilters.dia_hasta" type="date" />
          </div>
        </template>
      </div>
      <div class="actions-row">
        <button type="button" :disabled="loading" @click="filterGrouped">Filtrar</button>
        <button class="secondary" type="button" @click="clearGrouped">Limpiar</button>
        <button class="secondary" type="button" @click="exportGrouped('excel')">Excel</button>
        <button class="secondary" type="button" @click="exportGrouped('pdf')">PDF</button>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th v-for="column in groupedColumns" :key="String(column.key)">{{ column.label }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in groupedRows()" :key="index">
              <td v-for="column in groupedColumns" :key="String(column.key)">{{ row[String(column.key)] ?? 0 }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>
