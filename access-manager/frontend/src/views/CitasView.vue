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
  if (!form.complejo_id) return [];
  return pisos.value
    .filter((item) => item.complejo_id === form.complejo_id && (!form.torre_id || item.torre_id === form.torre_id))
    .sort((a, b) => a.numero - b.numero);
});

const filteredConsultorios = computed(() => {
  if (!form.complejo_id || !form.piso_id) return [];
  return consultorios.value
    .filter((item) => item.complejo_id === form.complejo_id && item.piso_id === form.piso_id)
    .sort((a, b) => a.codigo.localeCompare(b.codigo));
});

function institucionLabel(item: Institucion) {
  return item.razon_social ? `${item.nombre} · ${item.razon_social}` : item.nombre;
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

function matchByLabel<T>(rows: T[], text: string, labeler: (item: T) => string) {
  const normalized = text.trim().toLowerCase();
  return rows.find((item) => {
    const label = labeler(item).toLowerCase();
    return label === normalized || label.split(' · ')[0] === normalized;
  });
}

function setAutocompleteLabels() {
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

function clearLocation(from: 'institucion' | 'complejo' | 'torre' | 'piso') {
  if (from === 'institucion') {
    form.complejo_id = '';
    complejoSearch.value = '';
  }
  if (from === 'institucion' || from === 'complejo') {
    form.torre_id = '';
    torreSearch.value = '';
  }
  if (from === 'institucion' || from === 'complejo' || from === 'torre') {
    form.piso_id = '';
    pisoSearch.value = '';
  }
  form.consultorio_id = '';
  consultorioSearch.value = '';
}

function syncInstitution() {
  const match = matchByLabel(instituciones.value, institucionSearch.value, institucionLabel);
  form.institucion_id = match?.id ?? '';
  if (!filteredComplejos.value.some((item) => item.id === form.complejo_id)) {
    clearLocation('institucion');
  }
}

function syncComplex() {
  const match = matchByLabel(filteredComplejos.value, complejoSearch.value, (item) => item.nombre);
  form.complejo_id = match?.id ?? '';
  if (!filteredTorres.value.some((item) => item.id === form.torre_id)) {
    clearLocation('complejo');
  }
}

function syncTorre() {
  const match = matchByLabel(filteredTorres.value, torreSearch.value, torreLabel);
  form.torre_id = match?.id ?? '';
  if (!filteredPisos.value.some((item) => item.id === form.piso_id)) {
    clearLocation('torre');
  }
}

function syncPiso() {
  const match = matchByLabel(filteredPisos.value, pisoSearch.value, pisoLabel);
  form.piso_id = match?.id ?? '';
  if (match && !form.torre_id) {
    form.torre_id = match.torre_id;
    const torre = torres.value.find((item) => item.id === match.torre_id);
    torreSearch.value = torre ? torreLabel(torre) : '';
  }
  if (!filteredConsultorios.value.some((item) => item.id === form.consultorio_id)) {
    clearLocation('piso');
  }
}

function syncConsultorio() {
  const match = matchByLabel(filteredConsultorios.value, consultorioSearch.value, consultorioLabel);
  form.consultorio_id = match?.id ?? '';
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
  const consultorio = consultorios.value[0];
  if (consultorio) {
    const piso = pisos.value.find((item) => item.id === consultorio.piso_id);
    form.complejo_id = consultorio.complejo_id;
    form.piso_id = consultorio.piso_id;
    form.torre_id = piso?.torre_id ?? '';
    form.consultorio_id = consultorio.id;
    form.institucion_id = complejos.value.find((item) => item.id === consultorio.complejo_id)?.institucion_id ?? '';
    return;
  }
  form.institucion_id = instituciones.value[0]?.id ?? '';
  form.complejo_id = filteredComplejos.value[0]?.id ?? '';
  form.torre_id = filteredTorres.value[0]?.id ?? '';
  form.piso_id = filteredPisos.value[0]?.id ?? '';
  form.consultorio_id = filteredConsultorios.value[0]?.id ?? '';
}

function resetForm() {
  form.tipo = 'PROGRAMADA';
  form.fecha_cita = todayLocalIso();
  form.hora_cita = '09:00';
  form.duracion_estimada = 30;
  form.origen = 'WEB';
  form.notas_operativas = '';
  form.medico_id = defaultMedicoId();
  form.paciente_id = '';
  pacienteSearch.value = '';
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
    citas.value = await listCitas(tableRequestFilters());
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar citas.';
  }
}

async function load() {
  error.value = '';
  try {
    const [citasData, userData, medicosData, consultoriosData, institucionesData, complejosData, torresData, pisosData] = await Promise.all([
      listCitas(tableRequestFilters()),
      getCurrentUser(),
      listAccessibleMedicos(),
      listAccessibleConsultorios(),
      listAccessibleInstituciones(),
      listAccessibleComplejos(),
      listAccessibleTorres(),
      listAccessiblePisos(),
    ]);
    citas.value = citasData;
    currentUser.value = userData;
    medicos.value = medicosData;
    consultorios.value = consultoriosData;
    instituciones.value = institucionesData;
    complejos.value = complejosData;
    torres.value = torresData;
    pisos.value = pisosData;
    form.medico_id = defaultMedicoId();
    await loadPatientsForMedico();
    resetForm();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar citas.';
  }
}

async function onMedicoChange() {
  error.value = '';
  form.paciente_id = '';
  pacienteSearch.value = '';
  try {
    await loadPatientsForMedico();
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
    resetForm();
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
          <select id="medico" v-model="form.medico_id" required @change="onMedicoChange">
            <option value="">Seleccione médico</option>
            <option v-for="medico in medicos" :key="medico.id" :value="medico.id">
              {{ medicoLabel(medico) }}
            </option>
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
            <option v-for="paciente in pacientes" :key="paciente.id" :value="patientOptionLabel(paciente)" />
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
          <label for="piso">Piso</label>
          <input
            id="piso"
            v-model="pisoSearch"
            list="cita-pisos"
            required
            :disabled="!form.complejo_id"
            @input="syncPiso"
            @change="syncPiso"
          />
          <datalist id="cita-pisos">
            <option v-for="piso in filteredPisos" :key="piso.id" :value="pisoLabel(piso)" />
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
              <tr v-for="cita in citas" :key="cita.id">
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
