<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import {
  listAccessibleComplejos,
  listAccessibleInstituciones,
  listAccessiblePisos,
  listAccessibleTorres,
  listReceptionCitas,
  listReceptionOptions,
  receptionCancelCheckin,
  receptionCheckin,
  type Complejo,
  type Institucion,
  type Piso,
  type ReceptionCita,
  type ReceptionCitaFilters,
  type ReceptionOption,
  type Torre,
} from '../api/client';
import { localTimeMinusHours } from '../dateUtils';
import { pisoCodigoVisibleLabel, sortPisosByCodigo } from '../floorLabels';

const instituciones = ref<Institucion[]>([]);
const complejos = ref<Complejo[]>([]);
const torres = ref<Torre[]>([]);
const pisos = ref<Piso[]>([]);
const pacientes = ref<ReceptionOption[]>([]);
const medicos = ref<ReceptionOption[]>([]);
const consultorios = ref<ReceptionOption[]>([]);
const rows = ref<ReceptionCita[]>([]);
const total = ref(0);
const loading = ref(false);
const error = ref('');
const optionsError = ref('');
const message = ref('');
let optionsRequestToken = 0;

const search = reactive({
  institucion: '',
  campus: '',
  torre: '',
  piso: '',
  paciente: '',
  medico: '',
  consultorio: '',
});

const filters = reactive({
  institucion_id: '',
  complejo_id: '',
  torre_id: '',
  piso_id: '',
  hora_inicio: localTimeMinusHours(1),
  sort_by: 'fecha_hora' as NonNullable<ReceptionCitaFilters['sort_by']>,
  sort_dir: 'asc' as NonNullable<ReceptionCitaFilters['sort_dir']>,
  limit: 20,
  offset: 0,
});

const scopedComplejos = computed(() =>
  filters.institucion_id ? sortByLabel(uniqueById(complejos.value.filter((item) => item.institucion_id === filters.institucion_id)), (item) => item.nombre) : [],
);
const scopedTorres = computed(() =>
  filters.complejo_id ? sortByLabel(uniqueById(torres.value.filter((item) => item.complejo_id === filters.complejo_id)), torreLabel) : [],
);
const scopedPisos = computed(() =>
  filters.complejo_id && filters.torre_id
    ? sortPisosByCodigo(uniqueById(pisos.value.filter((item) => item.complejo_id === filters.complejo_id && item.torre_id === filters.torre_id)))
    : [],
);
const currentPage = computed(() => Math.floor(filters.offset / filters.limit) + 1);
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / filters.limit)));
const rangeStart = computed(() => (total.value ? filters.offset + 1 : 0));
const rangeEnd = computed(() => Math.min(total.value, filters.offset + rows.value.length));

function matchByLabel<T extends { id: string }>(items: T[], text: string, labeler: (item: T) => string) {
  const normalized = text.trim().toLowerCase();
  return items.find((item) => labeler(item).trim().toLowerCase() === normalized) ?? null;
}

function optionId(options: ReceptionOption[], text: string) {
  return matchByLabel(options, text, (item) => item.label)?.id ?? '';
}

function uniqueById<T extends { id: string }>(rows: T[]) {
  const seen = new Set<string>();
  const result: T[] = [];
  for (const row of rows) {
    if (seen.has(row.id)) continue;
    seen.add(row.id);
    result.push(row);
  }
  return result;
}

function sortByLabel<T>(rows: T[], labeler: (item: T) => string) {
  return [...rows].sort((left, right) => labeler(left).localeCompare(labeler(right), 'es', { numeric: true, sensitivity: 'base' }));
}

function institucionLabel(item: Institucion) {
  return item.nombre;
}

function torreLabel(item: Torre) {
  return item.nombre;
}

function pisoLabel(item: Piso) {
  return pisoCodigoVisibleLabel(item);
}

function applySingleDefaults() {
  if (instituciones.value.length === 1) {
    filters.institucion_id = instituciones.value[0].id;
    search.institucion = institucionLabel(instituciones.value[0]);
  }
  if (scopedComplejos.value.length === 1) {
    filters.complejo_id = scopedComplejos.value[0].id;
    search.campus = scopedComplejos.value[0].nombre;
  }
  if (scopedTorres.value.length === 1) {
    filters.torre_id = scopedTorres.value[0].id;
    search.torre = torreLabel(scopedTorres.value[0]);
  }
  if (scopedPisos.value.length === 1) {
    filters.piso_id = scopedPisos.value[0].id;
    search.piso = pisoLabel(scopedPisos.value[0]);
  }
}

function clearAppointmentSearch() {
  search.paciente = '';
  search.medico = '';
  search.consultorio = '';
}

function clearReceptionOptions() {
  pacientes.value = [];
  medicos.value = [];
  consultorios.value = [];
}

function syncInstitucion() {
  const match = matchByLabel(instituciones.value, search.institucion, institucionLabel);
  filters.institucion_id = match?.id ?? '';
  search.campus = '';
  search.torre = '';
  search.piso = '';
  clearAppointmentSearch();
  filters.complejo_id = '';
  filters.torre_id = '';
  filters.piso_id = '';
  applySingleDefaults();
  if (search.institucion.trim() && !match) {
    clearReceptionOptions();
    return;
  }
  void refreshOptions();
}

function syncCampus() {
  const match = matchByLabel(scopedComplejos.value, search.campus, (item) => item.nombre);
  filters.complejo_id = match?.id ?? '';
  search.torre = '';
  search.piso = '';
  clearAppointmentSearch();
  filters.torre_id = '';
  filters.piso_id = '';
  applySingleDefaults();
  if (search.campus.trim() && !match) {
    clearReceptionOptions();
    return;
  }
  void refreshOptions();
}

function syncTorre() {
  const match = matchByLabel(scopedTorres.value, search.torre, torreLabel);
  filters.torre_id = match?.id ?? '';
  search.piso = '';
  clearAppointmentSearch();
  filters.piso_id = '';
  applySingleDefaults();
  if (search.torre.trim() && !match) {
    clearReceptionOptions();
    return;
  }
  void refreshOptions();
}

function syncPiso() {
  const match = matchByLabel(scopedPisos.value, search.piso, pisoLabel);
  filters.piso_id = match?.id ?? '';
  clearAppointmentSearch();
  if (search.piso.trim() && !match) {
    clearReceptionOptions();
    return;
  }
  void refreshOptions();
}

function locationParams(): ReceptionCitaFilters {
  return {
    institucion_id: filters.institucion_id,
    complejo_id: filters.complejo_id,
    torre_id: filters.torre_id,
    piso_id: filters.piso_id,
    hora_inicio: filters.hora_inicio,
  };
}

function requestParams(): ReceptionCitaFilters {
  const pacienteId = optionId(pacientes.value, search.paciente);
  const medicoId = optionId(medicos.value, search.medico);
  const consultorioId = optionId(consultorios.value, search.consultorio);
  return {
    ...locationParams(),
    paciente_id: pacienteId,
    paciente: pacienteId ? undefined : search.paciente.trim(),
    medico_id: medicoId,
    medico: medicoId ? undefined : search.medico.trim(),
    consultorio_id: consultorioId,
    consultorio: consultorioId ? undefined : search.consultorio.trim(),
    sort_by: filters.sort_by,
    sort_dir: filters.sort_dir,
    limit: filters.limit,
    offset: filters.offset,
  };
}

async function refreshOptions() {
  const requestToken = ++optionsRequestToken;
  optionsError.value = '';
  try {
    const data = await listReceptionOptions(locationParams());
    if (requestToken !== optionsRequestToken) return;
    pacientes.value = data.pacientes;
    medicos.value = data.medicos;
    consultorios.value = data.consultorios;
  } catch (err) {
    if (requestToken !== optionsRequestToken) return;
    clearReceptionOptions();
    optionsError.value = err instanceof Error ? err.message : 'No fue posible cargar las opciones de recepción.';
  }
}

async function loadRows() {
  loading.value = true;
  error.value = '';
  try {
    const data = await listReceptionCitas(requestParams());
    rows.value = data.items;
    total.value = data.total;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar citas de recepción.';
  } finally {
    loading.value = false;
  }
}

async function searchRows() {
  filters.offset = 0;
  await loadRows();
}

async function clearFilters() {
  search.institucion = '';
  search.campus = '';
  search.torre = '';
  search.piso = '';
  search.paciente = '';
  search.medico = '';
  search.consultorio = '';
  optionsError.value = '';
  filters.institucion_id = '';
  filters.complejo_id = '';
  filters.torre_id = '';
  filters.piso_id = '';
  filters.hora_inicio = localTimeMinusHours(1);
  filters.limit = 20;
  filters.offset = 0;
  filters.sort_by = 'fecha_hora';
  filters.sort_dir = 'asc';
  applySingleDefaults();
  await refreshOptions();
  await loadRows();
}

async function loadCatalogs() {
  const [institucionesData, complejosData, torresData, pisosData] = await Promise.all([
    listAccessibleInstituciones(),
    listAccessibleComplejos(),
    listAccessibleTorres(),
    listAccessiblePisos(),
  ]);
  instituciones.value = institucionesData;
  complejos.value = complejosData;
  torres.value = torresData;
  pisos.value = pisosData;
  applySingleDefaults();
}

async function runCheckin(cita: ReceptionCita) {
  loading.value = true;
  error.value = '';
  message.value = '';
  try {
    const response = await receptionCheckin(cita.id);
    message.value = response.mensaje || 'Check-in registrado.';
    await refreshOptions();
    await loadRows();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible registrar el check-in.';
  } finally {
    loading.value = false;
  }
}

async function undoCheckin(cita: ReceptionCita) {
  loading.value = true;
  error.value = '';
  message.value = '';
  try {
    const response = await receptionCancelCheckin(cita.id);
    message.value = response.mensaje;
    await refreshOptions();
    await loadRows();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible deshacer el check-in.';
  } finally {
    loading.value = false;
  }
}

function setSort(sortBy: NonNullable<ReceptionCitaFilters['sort_by']>) {
  if (filters.sort_by === sortBy) {
    filters.sort_dir = filters.sort_dir === 'asc' ? 'desc' : 'asc';
  } else {
    filters.sort_by = sortBy;
    filters.sort_dir = 'asc';
  }
  filters.offset = 0;
  void loadRows();
}

function sortIndicator(sortBy: NonNullable<ReceptionCitaFilters['sort_by']>) {
  if (filters.sort_by !== sortBy) return '';
  return filters.sort_dir === 'asc' ? ' ↑' : ' ↓';
}

function setPageSize(size: number) {
  filters.limit = size;
  filters.offset = 0;
  void loadRows();
}

function onPageSizeChange(event: Event) {
  const target = event.target as HTMLSelectElement | null;
  setPageSize(Number(target?.value || 20));
}

function previousPage() {
  filters.offset = Math.max(0, filters.offset - filters.limit);
  void loadRows();
}

function nextPage() {
  if (currentPage.value >= totalPages.value) return;
  filters.offset += filters.limit;
  void loadRows();
}

function formatDateTime(cita: ReceptionCita) {
  return `${cita.fecha_cita} ${cita.hora_cita.slice(0, 5)}`;
}

function checkinLabel(cita: ReceptionCita) {
  return cita.estado === 'LLEGO_LOBBY' ? 'Registrado' : 'Checkin';
}

onMounted(async () => {
  loading.value = true;
  try {
    await loadCatalogs();
    await refreshOptions();
    await loadRows();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible iniciar recepción.';
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Recepción</h1>
        <p>Registro de llegada y checkin de citas del día.</p>
      </div>
      <button class="secondary" type="button" @click="loadRows">Actualizar</button>
    </header>

    <form class="panel form" @submit.prevent="searchRows">
      <div class="form-grid">
        <div class="form-row">
          <label for="recepcion-institucion">Institución</label>
          <input id="recepcion-institucion" v-model="search.institucion" list="recepcion-instituciones" @input="syncInstitucion" @change="syncInstitucion" />
          <datalist id="recepcion-instituciones">
            <option v-for="item in instituciones" :key="item.id" :value="institucionLabel(item)" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="recepcion-campus">Campus</label>
          <input id="recepcion-campus" v-model="search.campus" list="recepcion-campus-options" :disabled="!filters.institucion_id" @input="syncCampus" @change="syncCampus" />
          <datalist id="recepcion-campus-options">
            <option v-for="item in scopedComplejos" :key="item.id" :value="item.nombre" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="recepcion-torre">Torre</label>
          <input id="recepcion-torre" v-model="search.torre" list="recepcion-torres" :disabled="!filters.complejo_id" @input="syncTorre" @change="syncTorre" />
          <datalist id="recepcion-torres">
            <option v-for="item in scopedTorres" :key="item.id" :value="torreLabel(item)" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="recepcion-piso">Piso</label>
          <input id="recepcion-piso" v-model="search.piso" list="recepcion-pisos" :disabled="!filters.torre_id" @input="syncPiso" @change="syncPiso" />
          <datalist id="recepcion-pisos">
            <option v-for="item in scopedPisos" :key="item.id" :value="pisoLabel(item)" />
          </datalist>
        </div>
      </div>

      <div class="form-grid">
        <div class="form-row">
          <label for="recepcion-paciente">Pacientes</label>
          <input id="recepcion-paciente" v-model="search.paciente" list="recepcion-pacientes" />
          <datalist id="recepcion-pacientes">
            <option v-for="item in pacientes" :key="item.id" :value="item.label" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="recepcion-medico">Médicos</label>
          <input id="recepcion-medico" v-model="search.medico" list="recepcion-medicos" />
          <datalist id="recepcion-medicos">
            <option v-for="item in medicos" :key="item.id" :value="item.label" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="recepcion-consultorio">Consultorios</label>
          <input id="recepcion-consultorio" v-model="search.consultorio" list="recepcion-consultorios" />
          <datalist id="recepcion-consultorios">
            <option v-for="item in consultorios" :key="item.id" :value="item.label" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="recepcion-hora-inicio">Hora de inicio</label>
          <input id="recepcion-hora-inicio" v-model="filters.hora_inicio" type="time" @change="refreshOptions" />
        </div>
      </div>

      <div class="actions-row">
        <button type="submit" :disabled="loading">{{ loading ? 'Buscando...' : 'Buscar' }}</button>
        <button class="secondary" type="button" @click="clearFilters">Limpiar</button>
      </div>
      <p v-if="message" class="success-message">{{ message }}</p>
      <p v-if="optionsError && optionsError !== error" class="error">{{ optionsError }}</p>
      <p v-if="error" class="error">{{ error }}</p>
    </form>

    <section class="panel table-panel">
      <div class="page-header compact">
        <div>
          <h2>Citas</h2>
          <p>{{ rangeStart }}-{{ rangeEnd }} de {{ total }} registros</p>
        </div>
        <label class="inline-field">
          Registros
          <select :value="filters.limit" @change="onPageSizeChange">
            <option :value="10">10</option>
            <option :value="20">20</option>
            <option :value="50">50</option>
          </select>
        </label>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Checkin</th>
              <th><button class="table-sort-button" type="button" @click="setSort('paciente')">Paciente{{ sortIndicator('paciente') }}</button></th>
              <th><button class="table-sort-button" type="button" @click="setSort('fecha_hora')">Fecha y hora{{ sortIndicator('fecha_hora') }}</button></th>
              <th>Consultorio</th>
              <th>Torre</th>
              <th>Piso</th>
              <th><button class="table-sort-button" type="button" @click="setSort('medico')">Médico{{ sortIndicator('medico') }}</button></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="cita in rows" :key="cita.id">
              <td>
                <div class="inline-actions">
                  <button class="small" type="button" :class="{ success: cita.estado === 'LLEGO_LOBBY' }" :disabled="loading || cita.estado === 'LLEGO_LOBBY'" @click="runCheckin(cita)">
                    {{ checkinLabel(cita) }}
                  </button>
                  <button v-if="cita.estado === 'LLEGO_LOBBY'" class="small secondary" type="button" :disabled="loading" @click="undoCheckin(cita)">
                    Deshacer
                  </button>
                </div>
              </td>
              <td>{{ cita.paciente }}</td>
              <td>{{ formatDateTime(cita) }}</td>
              <td>{{ cita.consultorio }}</td>
              <td>{{ cita.torre }}</td>
              <td>{{ cita.piso }}</td>
              <td>{{ cita.medico }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pagination-row">
        <span class="message">Página {{ currentPage }} de {{ totalPages }}</span>
        <div class="inline-actions">
          <button class="secondary small" type="button" :disabled="loading || filters.offset === 0" @click="previousPage">Anterior</button>
          <button class="secondary small" type="button" :disabled="loading || currentPage >= totalPages" @click="nextPage">Siguiente</button>
        </div>
      </div>
      <p v-if="!loading && rows.length === 0" class="message">No hay citas con estos filtros.</p>
    </section>
  </section>
</template>
