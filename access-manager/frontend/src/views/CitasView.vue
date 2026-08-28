<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import {
  ApiError,
  createCita,
  getCurrentUser,
  listAccessibleComplejos,
  listAccessibleConsultorios,
  listAccessibleInstituciones,
  listAccessibleMedicos,
  listAccessiblePisos,
  listAccessibleTorres,
  listCitas,
  listPacientes,
  type Cita,
  type Complejo,
  type Consultorio,
  type Institucion,
  type Medico,
  type Paciente,
  type Piso,
  type Torre,
  type Usuario,
} from '../api/client';
import { localTimeMinusHours, todayLocalIso } from '../dateUtils';
import { pisoCodigoVisibleLabel, sortPisosByCodigo } from '../floorLabels';

type DuplicateWarning = {
  mensaje: string;
  duplicados: Array<{
    cita_id: string;
    folio_turno: string;
    estado: string;
  }>;
};

type LocationCatalogData = {
  consultoriosData: Consultorio[];
  institucionesData: Institucion[];
  complejosData: Complejo[];
  torresData: Torre[];
  pisosData: Piso[];
};

type ResetFormOptions = {
  keepMedico?: boolean;
};

const citas = ref<Cita[]>([]);
const pacientes = ref<Paciente[]>([]);
const medicos = ref<Medico[]>([]);
const consultorios = ref<Consultorio[]>([]);
const instituciones = ref<Institucion[]>([]);
const complejos = ref<Complejo[]>([]);
const torres = ref<Torre[]>([]);
const pisos = ref<Piso[]>([]);
const currentUser = ref<Usuario | null>(null);
const error = ref('');
const message = ref('');
const duplicateWarning = ref<DuplicateWarning | null>(null);
const pacienteSearch = ref('');
const pacienteComboboxOpen = ref(false);
const medicoLocationSyncToken = ref(0);
const patientNotRegisteredMessage = 'Error: el paciente no está registrado. Verifique.';
const tablePageSize = 20;
const tablePage = ref(1);
const DEFAULT_APPOINTMENT_DURATION = 60;
const MIN_APPOINTMENT_DURATION = 15;
const MAX_APPOINTMENT_DURATION = 120;

const form = reactive({
  tipo: 'PROGRAMADA',
  paciente_id: '',
  medico_id: '',
  institucion_id: '',
  torre_id: '',
  consultorio_id: '',
  complejo_id: '',
  piso_id: '',
  fecha_cita: todayLocalIso(),
  hora_cita: '09:00',
  duracion_estimada: DEFAULT_APPOINTMENT_DURATION,
  origen: 'WEB',
  notas_operativas: '',
});

const tableFilters = reactive({
  medico_id: '',
  fecha_inicio: todayLocalIso(),
  hora_inicio: localTimeMinusHours(1),
});

const medicoOptions = computed(() => sortByLabel(medicos.value, medicoLabel));
const institutionOptions = computed(() => sortByLabel(instituciones.value, institucionLabel));

const filteredComplejos = computed(() => {
  if (!form.institucion_id) return [];
  return sortByLabel(
    uniqueById(complejos.value.filter((item) => item.institucion_id === form.institucion_id)),
    (item) => item.nombre,
  );
});

const filteredTorres = computed(() => {
  if (!form.complejo_id) return [];
  return sortByLabel(
    uniqueById(torres.value.filter((item) => item.complejo_id === form.complejo_id)),
    (item) => item.nombre,
  );
});

const filteredPisos = computed(() => {
  if (!form.complejo_id || !form.torre_id) return [];
  return sortPisosByCodigo(
    uniqueById(pisos.value.filter((item) => item.complejo_id === form.complejo_id && item.torre_id === form.torre_id)),
  );
});

const filteredConsultorios = computed(() => {
  if (!form.complejo_id || !form.piso_id) return [];
  return sortConsultoriosByCodigo(
    uniqueById(consultorios.value.filter((item) => item.complejo_id === form.complejo_id && item.piso_id === form.piso_id)),
  );
});

const visibleCitas = computed(() => uniqueById(citas.value));
const locationLockedUntilMedico = computed(() => !form.medico_id);
const selectedMedico = computed(() => medicos.value.find((item) => item.id === form.medico_id) ?? null);
const horaFin = computed(() => appointmentEndTime(form.hora_cita, Number(form.duracion_estimada)));
const selectedPaciente = computed(() => pacientes.value.find((item) => item.id === form.paciente_id) ?? null);
const selectedPacienteCelular = computed(() => selectedPaciente.value?.celular ?? '');
const canGoPreviousCitasPage = computed(() => tablePage.value > 1);
const canGoNextCitasPage = computed(() => citas.value.length === tablePageSize);

const pacienteOptions = computed(() => {
  const q = normalizeAutocompleteText(pacienteSearch.value);
  const rows = uniqueById(pacientes.value).sort((a, b) =>
    patientOptionLabel(a).localeCompare(patientOptionLabel(b), 'es', { sensitivity: 'base' }),
  );
  if (!q) return rows;
  return rows.filter((item) => normalizeAutocompleteText(patientOptionLabel(item)).includes(q));
});
const showPacienteOptions = computed(() => pacienteComboboxOpen.value && Boolean(form.medico_id));

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

function mergeUniqueById<T extends { id: string }>(first: T[], second: T[]) {
  return uniqueById([...first, ...second]);
}

function emptyLocationCatalogData(): LocationCatalogData {
  return {
    consultoriosData: [],
    institucionesData: [],
    complejosData: [],
    torresData: [],
    pisosData: [],
  };
}

function sortByLabel<T>(rows: T[], labeler: (item: T) => string) {
  return [...rows].sort((left, right) => labeler(left).localeCompare(labeler(right), 'es', { numeric: true, sensitivity: 'base' }));
}

function sortConsultoriosByCodigo(rows: Consultorio[]) {
  return [...rows].sort((left, right) => {
    const byCodigo = left.codigo.localeCompare(right.codigo, 'es', { numeric: true, sensitivity: 'base' });
    if (byCodigo !== 0) return byCodigo;
    return consultorioLabel(left).localeCompare(consultorioLabel(right), 'es', { numeric: true, sensitivity: 'base' });
  });
}

function institucionLabel(item: Institucion) {
  return item.nombre;
}

function pisoLabel(item: Piso) {
  return pisoCodigoVisibleLabel(item);
}

function consultorioLabel(item: Consultorio) {
  const visibleName = item.nombre_visible?.trim();
  return visibleName ? `${item.codigo} - ${visibleName}` : item.codigo;
}

function torreLabel(item: Torre) {
  return item.nombre;
}

function medicoLabel(item: Medico) {
  return [item.apellidos, item.nombre].filter(Boolean).join(' ');
}

function defaultDurationForMedico(medicoId = form.medico_id) {
  return medicos.value.find((item) => item.id === medicoId)?.duracion_cita_minutos ?? DEFAULT_APPOINTMENT_DURATION;
}

function appointmentEndTime(startTime: string, durationMinutes: number) {
  const [hourText, minuteText] = startTime.split(':');
  const hour = Number(hourText);
  const minute = Number(minuteText);
  if (!Number.isInteger(hour) || !Number.isInteger(minute) || !Number.isFinite(durationMinutes)) return '';
  const totalMinutes = hour * 60 + minute + Math.max(0, Math.trunc(durationMinutes));
  const normalized = ((totalMinutes % 1440) + 1440) % 1440;
  const endHour = String(Math.floor(normalized / 60)).padStart(2, '0');
  const endMinute = String(normalized % 60).padStart(2, '0');
  return `${endHour}:${endMinute}`;
}

function patientDisplayName(paciente: Paciente) {
  const legalName = [paciente.nombre, paciente.apellido_paterno, paciente.apellido_materno].filter(Boolean).join(' ');
  return paciente.nombre_preferido || legalName || paciente.folio_paciente;
}

function patientOptionLabel(paciente: Paciente) {
  const legalName = [paciente.apellido_paterno, paciente.apellido_materno, paciente.nombre].filter(Boolean).join(' ');
  const name = paciente.nombre_preferido && legalName ? `${legalName} · ${paciente.nombre_preferido}` : legalName || paciente.nombre_preferido || 'Sin nombre';
  return `${name} · ${paciente.folio_paciente}`;
}

function patientOptionMeta(paciente: Paciente) {
  return [paciente.folio_paciente, paciente.celular ? `Cel. ${paciente.celular}` : 'Sin celular'].join(' · ');
}

function statusLabel(status: string) {
  if (status === 'NO_LLEGO') return 'No Se Presentó';
  return status;
}

function normalizeAutocompleteText(text: string) {
  return text
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase();
}

function matchByLabel<T>(rows: T[], text: string, labeler: (item: T) => string) {
  const normalized = normalizeAutocompleteText(text);
  return rows.find((item) => {
    const label = normalizeAutocompleteText(labeler(item));
    return label === normalized || normalizeAutocompleteText(label.split(' · ')[0] ?? '') === normalized;
  });
}

function hasAnyRole(roleCodes: string[]) {
  const roles = new Set(currentUser.value?.role_codes ?? []);
  return roleCodes.some((role) => roles.has(role));
}

function isAdminUser() {
  return hasAnyRole(['ADMIN_SISTEMA', 'ADMIN_NEGOCIO']);
}

function isDoctorUser() {
  return hasAnyRole(['MEDICO']);
}

function syncPacienteLabel() {
  const paciente = pacientes.value.find((item) => item.id === form.paciente_id);
  pacienteSearch.value = paciente ? patientOptionLabel(paciente) : '';
}

function setInstitutionOption(item: Institucion | null) {
  form.institucion_id = item?.id ?? '';
}

function setComplexOption(item: Complejo | null) {
  form.complejo_id = item?.id ?? '';
}

function setTowerOption(item: Torre | null) {
  form.torre_id = item?.id ?? '';
}

function setPisoOption(item: Piso | null) {
  form.piso_id = item?.id ?? '';
  if (item) {
    const torre = torres.value.find((row) => row.id === item.torre_id) ?? null;
    setTowerOption(torre);
  }
}

function setConsultorioOption(item: Consultorio | null) {
  form.consultorio_id = item?.id ?? '';
}

function clearLocation(from: 'institucion' | 'complejo' | 'torre' | 'piso') {
  if (from === 'institucion') {
    setComplexOption(null);
  }
  if (from === 'institucion' || from === 'complejo') {
    setTowerOption(null);
  }
  if (from === 'institucion' || from === 'complejo' || from === 'torre') {
    setPisoOption(null);
  }
  setConsultorioOption(null);
}

function autoFillSingleConsultorio() {
  if (!form.piso_id) return;
  if (filteredConsultorios.value.length === 1) {
    setConsultorioOption(filteredConsultorios.value[0]);
  }
}

function autoFillSingleConsultorioInCurrentLocation() {
  const pisoIdsInTower = form.torre_id
    ? new Set(
        pisos.value
          .filter((piso) => piso.torre_id === form.torre_id && (!form.complejo_id || piso.complejo_id === form.complejo_id))
          .map((piso) => piso.id),
      )
    : null;
  const rows = uniqueById(consultorios.value).filter((consultorio) => {
    if (form.piso_id) return consultorio.piso_id === form.piso_id;
    if (pisoIdsInTower) return pisoIdsInTower.has(consultorio.piso_id);
    if (form.complejo_id) return consultorio.complejo_id === form.complejo_id;
    return true;
  });
  return rows.length === 1 && setLocationFromConsultorio(rows[0]);
}

function autoFillSinglePiso() {
  if (!form.complejo_id || !form.torre_id) return;
  if (filteredPisos.value.length === 1) {
    setPisoOption(filteredPisos.value[0]);
    autoFillSingleConsultorio();
  }
}

function autoFillSingleTower() {
  if (!form.complejo_id) return;
  if (filteredTorres.value.length === 1) {
    setTowerOption(filteredTorres.value[0]);
    autoFillSinglePiso();
  }
}

function autoFillSingleComplex() {
  if (!form.institucion_id) return;
  if (filteredComplejos.value.length === 1) {
    setComplexOption(filteredComplejos.value[0]);
    autoFillSingleTower();
  }
}

function autoFillSingleInstitution() {
  if (instituciones.value.length === 1) {
    setInstitutionOption(instituciones.value[0]);
    autoFillSingleComplex();
  }
}

function setLocationFromConsultorio(consultorio: Consultorio) {
  const piso = pisos.value.find((item) => item.id === consultorio.piso_id) ?? null;
  if (!piso) return false;
  const torre = torres.value.find((item) => item.id === piso.torre_id) ?? null;
  const complejo = complejos.value.find((item) => item.id === consultorio.complejo_id) ?? null;
  const institucion = complejo ? instituciones.value.find((item) => item.id === complejo.institucion_id) ?? null : null;
  if (!torre || !complejo || !institucion) return false;

  setInstitutionOption(institucion);
  setComplexOption(complejo);
  setTowerOption(torre);
  setPisoOption(piso);
  setConsultorioOption(consultorio);
  return true;
}

function setDefaultLocationFromCatalogs(data: LocationCatalogData) {
  const catalogInstituciones = uniqueById(data.institucionesData);
  const catalogComplejos = uniqueById(data.complejosData);
  const catalogTorres = uniqueById(data.torresData);
  const catalogPisos = uniqueById(data.pisosData);
  const catalogConsultorios = uniqueById(data.consultoriosData);
  const singleConsultorio = catalogConsultorios.length === 1 ? catalogConsultorios[0] : null;

  if (singleConsultorio) {
    const piso = catalogPisos.find((item) => item.id === singleConsultorio.piso_id) ?? null;
    const torre = piso ? catalogTorres.find((item) => item.id === piso.torre_id) ?? null : null;
    const complejo = catalogComplejos.find((item) => item.id === singleConsultorio.complejo_id) ?? null;
    const institucion = complejo ? catalogInstituciones.find((item) => item.id === complejo.institucion_id) ?? null : null;
    if (piso && torre && complejo && institucion) {
      setInstitutionOption(institucion);
      setComplexOption(complejo);
      setTowerOption(torre);
      setPisoOption(piso);
      setConsultorioOption(singleConsultorio);
      return;
    }
  }

  if (catalogInstituciones.length !== 1) return;
  const institucion = catalogInstituciones[0];
  setInstitutionOption(institucion);

  const institutionComplejos = uniqueById(catalogComplejos.filter((item) => item.institucion_id === institucion.id));
  if (institutionComplejos.length !== 1) return;
  const complejo = institutionComplejos[0];
  setComplexOption(complejo);

  const complexTorres = uniqueById(catalogTorres.filter((item) => item.complejo_id === complejo.id));
  if (complexTorres.length !== 1) return;
  const torre = complexTorres[0];
  setTowerOption(torre);

  const towerPisos = uniqueById(catalogPisos.filter((item) => item.complejo_id === complejo.id && item.torre_id === torre.id));
  if (towerPisos.length !== 1) return;
  const piso = towerPisos[0];
  setPisoOption(piso);

  const floorConsultorios = uniqueById(catalogConsultorios.filter((item) => item.complejo_id === complejo.id && item.piso_id === piso.id));
  if (floorConsultorios.length === 1) {
    setConsultorioOption(floorConsultorios[0]);
  }
}

function onInstitutionChange() {
  if (!filteredComplejos.value.some((item) => item.id === form.complejo_id)) {
    clearLocation('institucion');
  }
  autoFillSingleComplex();
}

function onComplexChange() {
  const selected = complejos.value.find((item) => item.id === form.complejo_id);
  if (selected) {
    setInstitutionOption(instituciones.value.find((item) => item.id === selected.institucion_id) ?? null);
  }
  if (!filteredTorres.value.some((item) => item.id === form.torre_id)) {
    setTowerOption(null);
  }
  if (!filteredPisos.value.some((item) => item.id === form.piso_id)) {
    clearLocation('torre');
  }
  autoFillSingleTower();
}

function onTowerChange() {
  if (!filteredPisos.value.some((item) => item.id === form.piso_id)) {
    clearLocation('torre');
  }
  autoFillSinglePiso();
}

function onPisoChange() {
  if (!filteredConsultorios.value.some((item) => item.id === form.consultorio_id)) {
    clearLocation('piso');
  }
  autoFillSingleConsultorio();
}

function syncPaciente() {
  const match = matchByLabel(pacientes.value, pacienteSearch.value, patientOptionLabel);
  form.paciente_id = match?.id ?? '';
}

function onPacienteInput() {
  pacienteComboboxOpen.value = true;
  syncPaciente();
}

function openPacienteCombobox() {
  if (form.medico_id) {
    pacienteComboboxOpen.value = true;
  }
}

function closePacienteCombobox() {
  pacienteComboboxOpen.value = false;
}

function selectPaciente(paciente: Paciente) {
  form.paciente_id = paciente.id;
  pacienteSearch.value = patientOptionLabel(paciente);
  pacienteComboboxOpen.value = false;
}

function patientIsRegisteredForSelectedMedico() {
  return Boolean(form.medico_id && form.paciente_id && pacientes.value.some((item) => item.id === form.paciente_id));
}

function defaultMedicoId() {
  if (isDoctorUser() && !isAdminUser()) {
    return medicos.value.find((medico) => medico.usuario_id === currentUser.value?.id)?.id ?? '';
  }
  return medicos.value.length === 1 ? medicos.value[0].id : '';
}

async function syncLocationForMedico(medicoId = form.medico_id) {
  const syncToken = ++medicoLocationSyncToken.value;
  setInstitutionOption(null);
  clearLocation('institucion');

  if (!medicoId) {
    applyLocationCatalogs(emptyLocationCatalogData());
    return;
  }

  const data = await fetchScopedLocationCatalogs(medicoId);
  if (syncToken !== medicoLocationSyncToken.value || form.medico_id !== medicoId) return;
  applyLocationCatalogs(data);
  setDefaultLocationFromCatalogs(data);
}

async function resetForm(options: ResetFormOptions = {}) {
  form.tipo = 'PROGRAMADA';
  form.fecha_cita = todayLocalIso();
  form.hora_cita = '09:00';
  form.origen = 'WEB';
  form.notas_operativas = '';
  if (!options.keepMedico) {
    form.medico_id = defaultMedicoId();
  } else if (!form.medico_id) {
    form.medico_id = defaultMedicoId();
  }
  form.duracion_estimada = defaultDurationForMedico(form.medico_id);
  form.paciente_id = '';
  pacienteSearch.value = '';
  await syncLocationForMedico(form.medico_id);
  duplicateWarning.value = null;
  syncPacienteLabel();
}

async function loadPatientsForMedico() {
  pacientes.value = form.medico_id ? await listPacientes({ medico_id: form.medico_id }) : [];
  if (!pacientes.value.some((item) => item.id === form.paciente_id)) {
    form.paciente_id = '';
    pacienteSearch.value = '';
  }
  pacienteComboboxOpen.value = false;
  syncPacienteLabel();
}

function tableRequestFilters() {
  return {
    medico_id: tableFilters.medico_id,
    fecha_inicio: tableFilters.fecha_inicio,
    hora_inicio: tableFilters.hora_inicio,
    limit: tablePageSize,
    offset: (tablePage.value - 1) * tablePageSize,
  };
}

function setTableFiltersForMedico(medicoId: string) {
  tableFilters.medico_id = medicoId;
  tableFilters.fecha_inicio = todayLocalIso();
  tableFilters.hora_inicio = localTimeMinusHours(1);
  tablePage.value = 1;
}

async function loadTable() {
  error.value = '';
  if (!tableFilters.medico_id) {
    citas.value = [];
    return;
  }
  try {
    citas.value = uniqueById(await listCitas(tableRequestFilters()));
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar citas.';
  }
}

async function loadTableFirstPage() {
  tablePage.value = 1;
  await loadTable();
}

async function loadTablePage(page: number) {
  tablePage.value = Math.max(1, page);
  await loadTable();
}

async function fetchLocationCatalogs(medicoId = form.medico_id): Promise<LocationCatalogData> {
  const params = medicoId ? { medico_id: medicoId } : {};
  const [consultoriosData, institucionesData, complejosData, torresData, pisosData] = await Promise.all([
    listAccessibleConsultorios(params),
    listAccessibleInstituciones(params),
    listAccessibleComplejos(params),
    listAccessibleTorres(params),
    listAccessiblePisos(params),
  ]);
  return { consultoriosData, institucionesData, complejosData, torresData, pisosData };
}

function locationParentsAreComplete(data: LocationCatalogData) {
  const institucionesById = new Set(data.institucionesData.map((item) => item.id));
  const complejosById = new Map(data.complejosData.map((item) => [item.id, item]));
  const torresById = new Map(data.torresData.map((item) => [item.id, item]));
  const pisosById = new Map(data.pisosData.map((item) => [item.id, item]));

  for (const consultorio of uniqueById(data.consultoriosData)) {
    const piso = pisosById.get(consultorio.piso_id);
    const complejo = complejosById.get(consultorio.complejo_id);
    if (!piso || !complejo) return false;
    if (!torresById.has(piso.torre_id) || !institucionesById.has(complejo.institucion_id)) return false;
  }

  for (const piso of uniqueById(data.pisosData)) {
    if (!torresById.has(piso.torre_id) || !complejosById.has(piso.complejo_id)) return false;
  }

  for (const torre of uniqueById(data.torresData)) {
    if (!complejosById.has(torre.complejo_id)) return false;
  }

  for (const complejo of uniqueById(data.complejosData)) {
    if (!institucionesById.has(complejo.institucion_id)) return false;
  }

  return true;
}

function locationParentSubset(primary: LocationCatalogData, available: LocationCatalogData): LocationCatalogData {
  const primaryConsultorios = uniqueById(primary.consultoriosData);
  const primaryPisos = uniqueById(primary.pisosData);
  const primaryTorres = uniqueById(primary.torresData);
  const primaryComplejos = uniqueById(primary.complejosData);
  const availablePisosById = new Map(available.pisosData.map((item) => [item.id, item]));
  const availableTorresById = new Map(available.torresData.map((item) => [item.id, item]));
  const availableComplejosById = new Map(available.complejosData.map((item) => [item.id, item]));
  const availableInstitucionesById = new Map(available.institucionesData.map((item) => [item.id, item]));

  const pisoIds = new Set([...primaryPisos.map((item) => item.id), ...primaryConsultorios.map((item) => item.piso_id)]);
  const parentPisos = uniqueById([...primaryPisos, ...[...pisoIds].map((id) => availablePisosById.get(id)).filter((item): item is Piso => Boolean(item))]);
  const torreIds = new Set([...primaryTorres.map((item) => item.id), ...parentPisos.map((item) => item.torre_id)]);
  const complejoIds = new Set([
    ...primaryComplejos.map((item) => item.id),
    ...primaryConsultorios.map((item) => item.complejo_id),
    ...parentPisos.map((item) => item.complejo_id),
  ]);
  const parentTorres = uniqueById(
    [...primaryTorres, ...[...torreIds].map((id) => availableTorresById.get(id)).filter((item): item is Torre => Boolean(item))],
  );
  parentTorres.forEach((item) => complejoIds.add(item.complejo_id));
  const parentComplejos = uniqueById(
    [...primaryComplejos, ...[...complejoIds].map((id) => availableComplejosById.get(id)).filter((item): item is Complejo => Boolean(item))],
  );
  const institucionIds = new Set(parentComplejos.map((item) => item.institucion_id));
  const parentInstituciones = [...institucionIds].map((id) => availableInstitucionesById.get(id)).filter((item): item is Institucion => Boolean(item));

  return {
    consultoriosData: [],
    institucionesData: parentInstituciones,
    complejosData: parentComplejos,
    torresData: parentTorres,
    pisosData: parentPisos,
  };
}

async function completeLocationCatalogParents(data: LocationCatalogData) {
  if (locationParentsAreComplete(data)) return data;
  try {
    return mergeLocationCatalogData(data, locationParentSubset(data, await fetchLocationCatalogs('')), true);
  } catch {
    return data;
  }
}

async function fetchScopedLocationCatalogs(medicoId = form.medico_id): Promise<LocationCatalogData> {
  if (!medicoId) return emptyLocationCatalogData();
  return completeLocationCatalogParents(await fetchLocationCatalogs(medicoId));
}

function applyLocationCatalogs(data: LocationCatalogData) {
  consultorios.value = uniqueById(data.consultoriosData);
  instituciones.value = uniqueById(data.institucionesData);
  complejos.value = uniqueById(data.complejosData);
  torres.value = uniqueById(data.torresData);
  pisos.value = uniqueById(data.pisosData);
}

function mergeLocationCatalogData(primary: LocationCatalogData, secondary: LocationCatalogData, keepPrimaryConsultorios = false) {
  return {
    consultoriosData: keepPrimaryConsultorios
      ? uniqueById(primary.consultoriosData)
      : mergeUniqueById(primary.consultoriosData, secondary.consultoriosData),
    institucionesData: mergeUniqueById(primary.institucionesData, secondary.institucionesData),
    complejosData: mergeUniqueById(primary.complejosData, secondary.complejosData),
    torresData: mergeUniqueById(primary.torresData, secondary.torresData),
    pisosData: mergeUniqueById(primary.pisosData, secondary.pisosData),
  };
}

async function load() {
  error.value = '';
  try {
    const [userData, medicosData] = await Promise.all([getCurrentUser(), listAccessibleMedicos()]);
    currentUser.value = userData;
    medicos.value = medicosData;
    await resetForm();
    if (form.medico_id) {
      setTableFiltersForMedico(form.medico_id);
    }
    await Promise.all([loadPatientsForMedico(), loadTable()]);
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar citas.';
  }
}

async function onMedicoChange(event?: Event) {
  error.value = '';
  const selectedMedicoId = event?.target instanceof HTMLSelectElement ? event.target.value : form.medico_id;
  form.medico_id = selectedMedicoId;
  form.duracion_estimada = defaultDurationForMedico(selectedMedicoId);
  form.paciente_id = '';
  pacienteSearch.value = '';
  setTableFiltersForMedico(selectedMedicoId);
  try {
    await Promise.all([loadPatientsForMedico(), syncLocationForMedico(selectedMedicoId), loadTable()]);
    syncPacienteLabel();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar pacientes del médico.';
  }
}

async function submit(confirmarDuplicado = false) {
  error.value = '';
  message.value = '';
  if (!confirmarDuplicado) {
    duplicateWarning.value = null;
  }
  syncPaciente();
  if (!patientIsRegisteredForSelectedMedico()) {
    error.value = patientNotRegisteredMessage;
    return;
  }
  const duration = Number(form.duracion_estimada);
  if (!Number.isInteger(duration) || duration < MIN_APPOINTMENT_DURATION || duration > MAX_APPOINTMENT_DURATION) {
    error.value = `La duración debe estar entre ${MIN_APPOINTMENT_DURATION} y ${MAX_APPOINTMENT_DURATION} minutos.`;
    return;
  }
  try {
    const { institucion_id: _institucionId, torre_id: _torreId, ...payload } = form;
    await createCita({ ...payload }, confirmarDuplicado);
    message.value = 'Cita creada.';
    duplicateWarning.value = null;
    await resetForm({ keepMedico: true });
    if (form.medico_id) {
      setTableFiltersForMedico(form.medico_id);
    }
    await loadTable();
  } catch (err) {
    const duplicate = duplicateDetail(err);
    if (duplicate) {
      duplicateWarning.value = duplicate;
      return;
    }
    const errorText = err instanceof Error ? err.message : '';
    error.value = errorText.includes('paciente no está asignado') ? patientNotRegisteredMessage : errorText || 'No fue posible crear la cita.';
  }
}

function clearTableFilters() {
  setTableFiltersForMedico(form.medico_id);
  void loadTable();
}

function duplicateDetail(err: unknown): DuplicateWarning | null {
  if (!(err instanceof ApiError) || err.status !== 409 || !err.detail || typeof err.detail !== 'object') {
    return null;
  }
  const detail = err.detail as Partial<DuplicateWarning>;
  if (typeof detail.mensaje !== 'string' || !Array.isArray(detail.duplicados)) {
    return null;
  }
  return {
    mensaje: detail.mensaje,
    duplicados: detail.duplicados.filter((item) => item && typeof item === 'object') as DuplicateWarning['duplicados'],
  };
}

onMounted(load);
</script>

<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1>Citas</h1>
        <p>Agenda programada y espontánea con folio corto automático.</p>
      </div>
    </div>

    <div class="grid catalog-grid">
      <form class="panel form" @submit.prevent="submit(false)">
        <h2>Crear cita</h2>
        <div class="form-grid">
          <div class="form-row">
            <label for="tipo">Tipo</label>
            <select id="tipo" v-model="form.tipo">
              <option value="PROGRAMADA">Programada</option>
              <option value="ESPONTANEA">Espontánea</option>
            </select>
          </div>
          <div class="form-row">
            <label for="fecha">Fecha</label>
            <input id="fecha" v-model="form.fecha_cita" type="date" required />
          </div>
          <div class="form-row">
            <label for="hora">Hora</label>
            <input id="hora" v-model="form.hora_cita" type="time" required />
          </div>
          <div class="form-row">
            <label for="duracion">Duración</label>
            <input
              id="duracion"
              v-model.number="form.duracion_estimada"
              type="number"
              :min="MIN_APPOINTMENT_DURATION"
              :max="MAX_APPOINTMENT_DURATION"
              required
            />
          </div>
          <div class="form-row">
            <label for="hora-fin">Hora fin</label>
            <input id="hora-fin" :value="horaFin" type="time" readonly />
          </div>
        </div>
        <p v-if="selectedMedico" class="message">Duración por omisión del médico: {{ selectedMedico.duracion_cita_minutos }} min.</p>
        <div class="form-row">
          <label for="medico">Médico</label>
          <select
            id="medico"
            v-model="form.medico_id"
            required
            :disabled="medicos.length === 0"
            @change="onMedicoChange"
          >
            <option value="">Selecciona médico</option>
            <option v-for="medico in medicoOptions" :key="medico.id" :value="medico.id">{{ medicoLabel(medico) }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="paciente">Paciente</label>
          <div class="combobox">
            <input
              id="paciente"
              v-model="pacienteSearch"
              autocomplete="off"
              required
              role="combobox"
              aria-controls="cita-pacientes"
              :aria-expanded="showPacienteOptions"
              :disabled="!form.medico_id || pacientes.length === 0"
              placeholder="Apellido o nombre"
              @focus="openPacienteCombobox"
              @input="onPacienteInput"
              @change="syncPaciente"
              @blur="closePacienteCombobox"
            />
            <div v-if="showPacienteOptions" id="cita-pacientes" class="combobox-list" role="listbox">
              <button
                v-for="paciente in pacienteOptions"
                :key="paciente.id"
                class="combobox-option"
                :class="{ selected: paciente.id === form.paciente_id }"
                type="button"
                role="option"
                :aria-selected="paciente.id === form.paciente_id"
                @mousedown.prevent="selectPaciente(paciente)"
              >
                <span class="combobox-option-title">{{ patientOptionLabel(paciente) }}</span>
                <span class="combobox-option-meta">{{ patientOptionMeta(paciente) }}</span>
              </button>
              <div v-if="pacienteOptions.length === 0" class="combobox-empty">Sin pacientes registrados para este médico.</div>
            </div>
          </div>
        </div>
        <div class="form-row">
          <label for="paciente-celular">Celular</label>
          <input id="paciente-celular" :value="selectedPacienteCelular" readonly placeholder="-" />
        </div>
        <div class="form-row">
          <label for="institucion">Institución</label>
          <select
            id="institucion"
            v-model="form.institucion_id"
            required
            :disabled="locationLockedUntilMedico || institutionOptions.length === 0"
            @change="onInstitutionChange"
          >
            <option value="">Selecciona institución</option>
            <option v-for="institucion in institutionOptions" :key="institucion.id" :value="institucion.id">
              {{ institucionLabel(institucion) }}
            </option>
          </select>
        </div>
        <div class="form-row">
          <label for="complejo">Campus</label>
          <select
            id="complejo"
            v-model="form.complejo_id"
            required
            :disabled="locationLockedUntilMedico || !form.institucion_id"
            @change="onComplexChange"
          >
            <option value="">Selecciona campus</option>
            <option v-for="complejo in filteredComplejos" :key="complejo.id" :value="complejo.id">{{ complejo.nombre }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="torre">Torre</label>
          <select
            id="torre"
            v-model="form.torre_id"
            required
            :disabled="locationLockedUntilMedico || !form.complejo_id"
            @change="onTowerChange"
          >
            <option value="">Selecciona torre</option>
            <option v-for="torre in filteredTorres" :key="torre.id" :value="torre.id">{{ torreLabel(torre) }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="piso">Piso</label>
          <select
            id="piso"
            v-model="form.piso_id"
            required
            :disabled="locationLockedUntilMedico || !form.torre_id"
            @change="onPisoChange"
          >
            <option value="">Selecciona piso</option>
            <option v-for="piso in filteredPisos" :key="piso.id" :value="piso.id">{{ pisoLabel(piso) }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="consultorio">Consultorio</label>
          <select
            id="consultorio"
            v-model="form.consultorio_id"
            required
            :disabled="locationLockedUntilMedico || !form.piso_id"
          >
            <option value="">Selecciona consultorio</option>
            <option
              v-for="consultorio in filteredConsultorios"
              :key="consultorio.id"
              :value="consultorio.id"
            >
              {{ consultorioLabel(consultorio) }}
            </option>
          </select>
        </div>
        <div class="form-row">
          <label for="notas">Notas operativas</label>
          <textarea id="notas" v-model="form.notas_operativas" rows="3" />
        </div>
        <div class="actions-row">
          <button type="submit">✓ Guardar</button>
          <button class="danger solid" type="button" @click="resetForm()">× Cancelar</button>
        </div>
        <div v-if="duplicateWarning" class="duplicate-warning">
          <div>
            <strong>{{ duplicateWarning.mensaje }}</strong>
            <ul>
              <li v-for="item in duplicateWarning.duplicados" :key="item.cita_id">
                {{ item.folio_turno }} · {{ statusLabel(item.estado) }}
              </li>
            </ul>
          </div>
          <div class="actions-row">
            <button class="success" type="button" @click="submit(true)">✓ Confirmar</button>
            <button class="danger solid" type="button" @click="duplicateWarning = null">× Cancelar</button>
          </div>
        </div>
        <p v-if="message" class="message">{{ message }}</p>
        <p v-if="error" class="error">{{ error }}</p>
      </form>

      <div class="panel table-panel">
        <div class="page-header compact">
          <h2>Citas</h2>
          <form class="inline-actions" @submit.prevent="loadTableFirstPage">
            <label class="inline-field">
              Fecha inicio
              <input v-model="tableFilters.fecha_inicio" type="date" />
            </label>
            <label class="inline-field">
              Hora inicio
              <input v-model="tableFilters.hora_inicio" type="time" />
            </label>
            <button type="submit">Filtrar</button>
            <button class="secondary" type="button" @click="clearTableFilters">Limpiar</button>
          </form>
        </div>
        <p v-if="!tableFilters.medico_id" class="message">Selecciona un médico para cargar citas.</p>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Hora</th>
                <th>Turno</th>
                <th>Paciente</th>
                <th>Consultorio</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="cita in visibleCitas" :key="cita.id">
                <td>{{ cita.fecha_cita }}</td>
                <td>{{ cita.hora_cita.slice(0, 5) }}</td>
                <td>{{ cita.folio_turno }}</td>
                <td>{{ cita.paciente || cita.paciente_id }}</td>
                <td>{{ cita.consultorio || cita.consultorio_id }}</td>
                <td><span class="status muted">{{ statusLabel(cita.estado) }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="pagination-row">
          <span>Página {{ tablePage }}</span>
          <div class="actions-row">
            <button class="secondary" type="button" :disabled="!canGoPreviousCitasPage" @click="loadTablePage(tablePage - 1)">
              Anterior
            </button>
            <button class="secondary" type="button" :disabled="!canGoNextCitasPage" @click="loadTablePage(tablePage + 1)">
              Siguiente
            </button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
