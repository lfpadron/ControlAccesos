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

type DuplicateWarning = {
  mensaje: string;
  duplicados: Array<{
    cita_id: string;
    folio_turno: string;
    estado: string;
  }>;
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
const institucionSearch = ref('');
const complejoSearch = ref('');
const torreSearch = ref('');
const pisoSearch = ref('');
const consultorioSearch = ref('');
const pacienteSearch = ref('');
const medicoSearch = ref('');
const locationCatalogMedicoId = ref<string | null>(null);

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

const filteredComplejos = computed(() => {
  if (!form.institucion_id) return [];
  return complejos.value.filter((item) => item.institucion_id === form.institucion_id);
});

const filteredTorres = computed(() => {
  if (!form.complejo_id) return [];
  return torres.value.filter((item) => item.complejo_id === form.complejo_id).sort((a, b) => a.nombre.localeCompare(b.nombre));
});

const filteredPisos = computed(() => {
  if (!form.complejo_id || !form.torre_id) return [];
  return pisos.value
    .filter((item) => item.complejo_id === form.complejo_id && item.torre_id === form.torre_id)
    .sort((a, b) => a.numero - b.numero);
});

const filteredConsultorios = computed(() => {
  if (!form.complejo_id || !form.piso_id) return [];
  return consultorios.value
    .filter((item) => item.complejo_id === form.complejo_id && item.piso_id === form.piso_id)
    .sort((a, b) => a.codigo.localeCompare(b.codigo));
});

const filteredMedicos = computed(() => {
  const q = normalizeAutocompleteText(medicoSearch.value);
  const rows = [...medicos.value].sort((a, b) => medicoLabel(a).localeCompare(medicoLabel(b), 'es', { sensitivity: 'base' }));
  if (!q) return rows;
  return rows.filter((item) =>
    normalizeAutocompleteText([item.nombre, item.apellidos, item.nombre_visible ?? '', medicoLabel(item)].join(' ')).includes(q),
  );
});

const visibleCitas = computed(() => uniqueById(citas.value));

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

function institucionLabel(item: Institucion) {
  return item.nombre;
}

function pisoLabel(item: Piso) {
  return [item.codigo || String(item.numero), item.nombre_visible].filter(Boolean).join(' · ');
}

function consultorioLabel(item: Consultorio) {
  return [item.codigo, item.nombre_visible].filter(Boolean).join(' · ');
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

function setAutocompleteLabels() {
  const medico = medicos.value.find((item) => item.id === form.medico_id);
  medicoSearch.value = medico ? medicoLabel(medico) : '';
  institucionSearch.value = instituciones.value.find((item) => item.id === form.institucion_id)?.nombre ?? '';
  complejoSearch.value = complejos.value.find((item) => item.id === form.complejo_id)?.nombre ?? '';
  const torre = torres.value.find((item) => item.id === form.torre_id);
  torreSearch.value = torre ? torreLabel(torre) : '';
  const piso = pisos.value.find((item) => item.id === form.piso_id);
  pisoSearch.value = piso ? pisoLabel(piso) : '';
  const consultorio = consultorios.value.find((item) => item.id === form.consultorio_id);
  consultorioSearch.value = consultorio ? consultorioLabel(consultorio) : '';
  const paciente = pacientes.value.find((item) => item.id === form.paciente_id);
  pacienteSearch.value = paciente ? patientOptionLabel(paciente) : '';
}

function setInstitutionOption(item: Institucion | null) {
  form.institucion_id = item?.id ?? '';
  institucionSearch.value = item ? institucionLabel(item) : '';
}

function setComplexOption(item: Complejo | null) {
  form.complejo_id = item?.id ?? '';
  complejoSearch.value = item?.nombre ?? '';
}

function setTowerOption(item: Torre | null) {
  form.torre_id = item?.id ?? '';
  torreSearch.value = item ? torreLabel(item) : '';
}

function setPisoOption(item: Piso | null) {
  form.piso_id = item?.id ?? '';
  pisoSearch.value = item ? pisoLabel(item) : '';
  if (item) {
    const torre = torres.value.find((row) => row.id === item.torre_id) ?? null;
    setTowerOption(torre);
  }
}

function setConsultorioOption(item: Consultorio | null) {
  form.consultorio_id = item?.id ?? '';
  consultorioSearch.value = item ? consultorioLabel(item) : '';
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

function syncInstitution() {
  const match = matchByLabel(instituciones.value, institucionSearch.value, institucionLabel);
  setInstitutionOption(match ?? null);
  if (!match) {
    clearLocation('institucion');
    return;
  }
  if (!filteredComplejos.value.some((item) => item.id === form.complejo_id)) {
    clearLocation('institucion');
  }
  autoFillSingleComplex();
}

function syncComplex() {
  const match = matchByLabel(filteredComplejos.value, complejoSearch.value, (item) => item.nombre);
  setComplexOption(match ?? null);
  if (!match) {
    clearLocation('complejo');
    return;
  }
  if (!filteredTorres.value.some((item) => item.id === form.torre_id)) {
    setTowerOption(null);
  }
  if (!filteredPisos.value.some((item) => item.id === form.piso_id)) {
    clearLocation('torre');
  }
  autoFillSingleTower();
}

function syncTorre() {
  const match = matchByLabel(filteredTorres.value, torreSearch.value, torreLabel);
  setTowerOption(match ?? null);
  if (!match) {
    clearLocation('torre');
    return;
  }
  if (!filteredPisos.value.some((item) => item.id === form.piso_id)) {
    clearLocation('torre');
  }
  autoFillSinglePiso();
}

function syncPiso() {
  const match = matchByLabel(filteredPisos.value, pisoSearch.value, pisoLabel);
  setPisoOption(match ?? null);
  if (!match) {
    clearLocation('piso');
    return;
  }
  if (!filteredConsultorios.value.some((item) => item.id === form.consultorio_id)) {
    clearLocation('piso');
  }
  autoFillSingleConsultorio();
}

function syncConsultorio() {
  const match = matchByLabel(filteredConsultorios.value, consultorioSearch.value, consultorioLabel);
  setConsultorioOption(match ?? null);
}

async function syncMedico() {
  const match = matchByLabel(medicos.value, medicoSearch.value, medicoLabel);
  const nextId = match?.id ?? '';
  if (form.medico_id === nextId) return;
  form.medico_id = nextId;
  await onMedicoChange();
}

function syncPaciente() {
  const match = matchByLabel(pacientes.value, pacienteSearch.value, patientOptionLabel);
  form.paciente_id = match?.id ?? '';
}

function defaultMedicoId() {
  const ownMedico = medicos.value.find((medico) => medico.usuario_id && medico.usuario_id === currentUser.value?.id);
  return ownMedico?.id ?? medicos.value[0]?.id ?? '';
}

function setDefaultLocation() {
  setInstitutionOption(null);
  clearLocation('institucion');
  if (consultorios.value.length === 1 && setLocationFromConsultorio(consultorios.value[0])) {
    setAutocompleteLabels();
    return;
  }
  autoFillSingleInstitution();
  setAutocompleteLabels();
}

async function resetForm() {
  form.tipo = 'PROGRAMADA';
  form.fecha_cita = todayLocalIso();
  form.hora_cita = '09:00';
  form.duracion_estimada = 30;
  form.origen = 'WEB';
  form.notas_operativas = '';
  form.medico_id = defaultMedicoId();
  form.paciente_id = '';
  pacienteSearch.value = '';
  if (locationCatalogMedicoId.value !== (form.medico_id || null)) {
    await loadLocationCatalogs(form.medico_id);
  }
  setDefaultLocation();
  duplicateWarning.value = null;
  setAutocompleteLabels();
}

async function loadPatientsForMedico() {
  pacientes.value = form.medico_id ? await listPacientes({ medico_id: form.medico_id }) : [];
  if (!pacientes.value.some((item) => item.id === form.paciente_id)) {
    form.paciente_id = '';
    pacienteSearch.value = '';
  }
  setAutocompleteLabels();
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
  const params = medicoId ? { medico_id: medicoId } : {};
  const [consultoriosData, institucionesData, complejosData, torresData, pisosData] = await Promise.all([
    listAccessibleConsultorios(params),
    listAccessibleInstituciones(params),
    listAccessibleComplejos(params),
    listAccessibleTorres(params),
    listAccessiblePisos(params),
  ]);
  consultorios.value = consultoriosData;
  instituciones.value = institucionesData;
  complejos.value = complejosData;
  torres.value = torresData;
  pisos.value = pisosData;
  locationCatalogMedicoId.value = medicoId || null;
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
    form.medico_id = defaultMedicoId();
    await loadLocationCatalogs(form.medico_id);
    await loadPatientsForMedico();
    await resetForm();
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
    setAutocompleteLabels();
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
          <input
            id="medico"
            v-model="medicoSearch"
            list="cita-medicos"
            required
            :disabled="medicos.length === 0"
            placeholder="Nombre o apellido"
            @input="syncMedico"
            @change="syncMedico"
          />
          <datalist id="cita-medicos">
            <option v-for="medico in filteredMedicos" :key="medico.id" :value="medicoLabel(medico)" />
          </datalist>
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
          <input
            id="institucion"
            v-model="institucionSearch"
            list="cita-instituciones"
            required
            @input="syncInstitution"
            @change="syncInstitution"
          />
          <datalist id="cita-instituciones">
            <option v-for="institucion in instituciones" :key="institucion.id" :value="institucionLabel(institucion)" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="complejo">Campus</label>
          <input
            id="complejo"
            v-model="complejoSearch"
            list="cita-complejos"
            required
            :disabled="!form.institucion_id"
            @input="syncComplex"
            @change="syncComplex"
          />
          <datalist id="cita-complejos">
            <option v-for="complejo in filteredComplejos" :key="complejo.id" :value="complejo.nombre" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="torre">Torre</label>
          <input
            id="torre"
            v-model="torreSearch"
            list="cita-torres"
            required
            :disabled="!form.complejo_id"
            @input="syncTorre"
            @change="syncTorre"
          />
          <datalist id="cita-torres">
            <option v-for="torre in filteredTorres" :key="torre.id" :value="torreLabel(torre)" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="piso">Piso</label>
          <input
            id="piso"
            v-model="pisoSearch"
            list="cita-pisos"
            required
            :disabled="!form.torre_id"
            @input="syncPiso"
            @change="syncPiso"
          />
          <datalist id="cita-pisos">
            <option v-for="piso in filteredPisos" :key="piso.id" :value="pisoLabel(piso)" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="consultorio">Consultorio</label>
          <input
            id="consultorio"
            v-model="consultorioSearch"
            list="cita-consultorios"
            required
            :disabled="!form.piso_id"
            @input="syncConsultorio"
            @change="syncConsultorio"
          />
          <datalist id="cita-consultorios">
            <option
              v-for="consultorio in filteredConsultorios"
              :key="consultorio.id"
              :value="consultorioLabel(consultorio)"
            />
          </datalist>
        </div>
        <div class="form-row">
          <label for="notas">Notas operativas</label>
          <textarea id="notas" v-model="form.notas_operativas" rows="3" />
        </div>
        <div class="actions-row">
          <button type="submit">✓ Guardar</button>
          <button class="danger solid" type="button" @click="resetForm">× Cancelar</button>
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
