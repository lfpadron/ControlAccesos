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
const locationCatalogMedicoId = ref<string | null>(null);
const locationCatalogsLoaded = ref(false);

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
  duracion_estimada: 30,
  origen: 'WEB',
  notas_operativas: '',
});

const tableFilters = reactive({
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
const requiresMedicoSelectionForLocation = computed(() => shouldRequireMedicoSelectionForLocation());
const locationLockedUntilMedico = computed(() => requiresMedicoSelectionForLocation.value && !form.medico_id);

const pacienteOptions = computed(() => {
  const q = normalizeAutocompleteText(pacienteSearch.value);
  const rows = uniqueById(pacientes.value).sort((a, b) =>
    patientOptionLabel(a).localeCompare(patientOptionLabel(b), 'es', { sensitivity: 'base' }),
  );
  if (!q) return rows;
  return rows.filter((item) => normalizeAutocompleteText(patientOptionLabel(item)).includes(q));
});

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

function patientDisplayName(paciente: Paciente) {
  const legalName = [paciente.nombre, paciente.apellido_paterno, paciente.apellido_materno].filter(Boolean).join(' ');
  return paciente.nombre_preferido || legalName || paciente.folio_paciente;
}

function patientOptionLabel(paciente: Paciente) {
  const legalName = [paciente.apellido_paterno, paciente.apellido_materno, paciente.nombre].filter(Boolean).join(' ');
  const name = paciente.nombre_preferido && legalName ? `${legalName} · ${paciente.nombre_preferido}` : legalName || paciente.nombre_preferido || 'Sin nombre';
  return `${name} · ${paciente.folio_paciente}`;
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

function isAssistantUser() {
  return hasAnyRole(['ASISTENTE', 'ASISTENTE_MEDICO', 'RECEPCIONISTA']);
}

function shouldRequireMedicoSelectionForLocation() {
  return isAssistantUser() && !isAdminUser() && medicos.value.length > 0;
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

function defaultMedicoId() {
  if (requiresMedicoSelectionForLocation.value) return '';
  return medicos.value.length === 1 ? medicos.value[0].id : '';
}

function setDefaultLocation() {
  setInstitutionOption(null);
  clearLocation('institucion');
  const uniqueConsultorios = uniqueById(consultorios.value);
  if (uniqueConsultorios.length === 1 && setLocationFromConsultorio(uniqueConsultorios[0])) return;
  autoFillSingleInstitution();
}

async function resetForm(options: ResetFormOptions = {}) {
  form.tipo = 'PROGRAMADA';
  form.fecha_cita = todayLocalIso();
  form.hora_cita = '09:00';
  form.duracion_estimada = 30;
  form.origen = 'WEB';
  form.notas_operativas = '';
  if (!options.keepMedico) {
    form.medico_id = defaultMedicoId();
  } else if (!form.medico_id) {
    form.medico_id = defaultMedicoId();
  }
  form.paciente_id = '';
  pacienteSearch.value = '';
  if (locationLockedUntilMedico.value) {
    applyLocationCatalogs(emptyLocationCatalogData(), '');
  } else if (!locationCatalogsLoaded.value || locationCatalogMedicoId.value !== (form.medico_id || null)) {
    await loadLocationCatalogs(form.medico_id);
  }
  setDefaultLocation();
  duplicateWarning.value = null;
  syncPacienteLabel();
}

async function loadPatientsForMedico() {
  pacientes.value = form.medico_id ? await listPacientes({ medico_id: form.medico_id }) : [];
  if (!pacientes.value.some((item) => item.id === form.paciente_id)) {
    form.paciente_id = '';
    pacienteSearch.value = '';
  }
  syncPacienteLabel();
}

function tableRequestFilters() {
  return {
    fecha_inicio: tableFilters.fecha_inicio,
    hora_inicio: tableFilters.hora_inicio,
  };
}

async function loadTable() {
  error.value = '';
  try {
    citas.value = uniqueById(await listCitas(tableRequestFilters()));
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar citas.';
  }
}

async function loadLocationCatalogs(medicoId = form.medico_id) {
  applyLocationCatalogs(await fetchScopedLocationCatalogs(medicoId), medicoId);
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
  if (requiresMedicoSelectionForLocation.value && !medicoId) return emptyLocationCatalogData();
  if (medicoId) return completeLocationCatalogParents(await fetchLocationCatalogs(medicoId));
  if (!shouldAggregateLocationCatalogsByMedico()) return completeLocationCatalogParents(await fetchLocationCatalogs(''));
  const catalogRows = await Promise.all(medicos.value.map((medico) => fetchLocationCatalogs(medico.id)));
  const mergedCatalogs = catalogRows.reduce((merged, catalogs) => mergeLocationCatalogData(merged, catalogs), emptyLocationCatalogData());
  return completeLocationCatalogParents(mergedCatalogs);
}

function shouldAggregateLocationCatalogsByMedico() {
  if (isAdminUser() || requiresMedicoSelectionForLocation.value) return false;
  return medicos.value.length > 0;
}

function applyLocationCatalogs(data: LocationCatalogData, medicoId = form.medico_id) {
  consultorios.value = uniqueById(data.consultoriosData);
  instituciones.value = uniqueById(data.institucionesData);
  complejos.value = uniqueById(data.complejosData);
  torres.value = uniqueById(data.torresData);
  pisos.value = uniqueById(data.pisosData);
  locationCatalogMedicoId.value = medicoId || null;
  locationCatalogsLoaded.value = true;
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
    const [citasData, userData, medicosData] = await Promise.all([
      listCitas(tableRequestFilters()),
      getCurrentUser(),
      listAccessibleMedicos(),
    ]);
    citas.value = uniqueById(citasData);
    currentUser.value = userData;
    medicos.value = medicosData;
    await resetForm();
    await loadPatientsForMedico();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar citas.';
  }
}

async function onMedicoChange() {
  error.value = '';
  form.paciente_id = '';
  pacienteSearch.value = '';
  try {
    setInstitutionOption(null);
    clearLocation('institucion');
    await Promise.all([loadPatientsForMedico(), loadLocationCatalogs(form.medico_id)]);
    setDefaultLocation();
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
  try {
    const { institucion_id: _institucionId, torre_id: _torreId, ...payload } = form;
    await createCita({ ...payload }, confirmarDuplicado);
    message.value = 'Cita creada.';
    duplicateWarning.value = null;
    await resetForm();
    await loadTable();
  } catch (err) {
    const duplicate = duplicateDetail(err);
    if (duplicate) {
      duplicateWarning.value = duplicate;
      return;
    }
    error.value = err instanceof Error ? err.message : 'No fue posible crear la cita.';
  }
}

function clearTableFilters() {
  tableFilters.fecha_inicio = todayLocalIso();
  tableFilters.hora_inicio = localTimeMinusHours(1);
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
        </div>
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
          <input
            id="paciente"
            v-model="pacienteSearch"
            list="cita-pacientes"
            required
            :disabled="!form.medico_id || pacientes.length === 0"
            placeholder="Apellido o nombre"
            @input="syncPaciente"
            @change="syncPaciente"
          />
          <datalist id="cita-pacientes">
            <option v-for="paciente in pacienteOptions" :key="paciente.id" :value="patientOptionLabel(paciente)" />
          </datalist>
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
          <form class="inline-actions" @submit.prevent="loadTable">
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
      </div>
    </div>
  </section>
</template>
