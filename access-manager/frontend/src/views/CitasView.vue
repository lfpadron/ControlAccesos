<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import {
  ApiError,
  createCita,
  listComplejos,
  listConsultorios,
  listCitas,
  listInstituciones,
  listMedicos,
  listPacientes,
  listPisos,
  type Cita,
  type Complejo,
  type Consultorio,
  type Institucion,
  type Medico,
  type Paciente,
  type Piso,
} from '../api/client';
import { todayLocalIso } from '../dateUtils';

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
const pisos = ref<Piso[]>([]);
const error = ref('');
const message = ref('');
const duplicateWarning = ref<DuplicateWarning | null>(null);
const institucionSearch = ref('');
const complejoSearch = ref('');
const pisoSearch = ref('');
const consultorioSearch = ref('');

const form = reactive({
  tipo: 'PROGRAMADA',
  paciente_id: '',
  medico_id: '',
  institucion_id: '',
  consultorio_id: '',
  complejo_id: '',
  piso_id: '',
  fecha_cita: todayLocalIso(),
  hora_cita: '09:00',
  duracion_estimada: 30,
  origen: 'WEB',
  notas_operativas: '',
});

const filteredComplejos = computed(() => {
  if (!form.institucion_id) return [];
  return complejos.value.filter((item) => item.institucion_id === form.institucion_id);
});

const filteredPisos = computed(() => {
  if (!form.complejo_id) return [];
  return pisos.value.filter((item) => item.complejo_id === form.complejo_id);
});

const filteredConsultorios = computed(() => {
  if (!form.complejo_id || !form.piso_id) return [];
  return consultorios.value.filter((item) => item.complejo_id === form.complejo_id && item.piso_id === form.piso_id);
});

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

function setAutocompleteLabels() {
  institucionSearch.value = instituciones.value.find((item) => item.id === form.institucion_id)?.nombre ?? '';
  complejoSearch.value = complejos.value.find((item) => item.id === form.complejo_id)?.nombre ?? '';
  pisoSearch.value = pisos.value.find((item) => item.id === form.piso_id)?.nombre_visible ?? '';
  const consultorio = consultorios.value.find((item) => item.id === form.consultorio_id);
  consultorioSearch.value = consultorio ? consultorio.nombre_visible || consultorio.codigo : '';
}

function clearLocation(from: 'institucion' | 'complejo' | 'piso') {
  if (from === 'institucion') {
    form.complejo_id = '';
    complejoSearch.value = '';
  }
  if (from === 'institucion' || from === 'complejo') {
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
  if (!filteredPisos.value.some((item) => item.id === form.piso_id)) {
    clearLocation('complejo');
  }
}

function syncPiso() {
  const match = matchByLabel(filteredPisos.value, pisoSearch.value, (item) => item.nombre_visible);
  form.piso_id = match?.id ?? '';
  if (!filteredConsultorios.value.some((item) => item.id === form.consultorio_id)) {
    clearLocation('piso');
  }
}

function syncConsultorio() {
  const match = matchByLabel(filteredConsultorios.value, consultorioSearch.value, (item) => item.nombre_visible || item.codigo);
  form.consultorio_id = match?.id ?? '';
}

function resetForm() {
  form.tipo = 'PROGRAMADA';
  form.fecha_cita = todayLocalIso();
  form.hora_cita = '09:00';
  form.duracion_estimada = 30;
  form.origen = 'WEB';
  form.notas_operativas = '';
  form.paciente_id = pacientes.value[0]?.id ?? '';
  form.medico_id = medicos.value[0]?.id ?? '';
  form.institucion_id = instituciones.value[0]?.id ?? '';
  form.complejo_id = filteredComplejos.value[0]?.id ?? '';
  form.piso_id = filteredPisos.value[0]?.id ?? '';
  form.consultorio_id = filteredConsultorios.value[0]?.id ?? '';
  duplicateWarning.value = null;
  setAutocompleteLabels();
}

async function load() {
  error.value = '';
  try {
    const [citasData, pacientesData, medicosData, consultoriosData, institucionesData, complejosData, pisosData] = await Promise.all([
      listCitas(),
      listPacientes(),
      listMedicos(),
      listConsultorios(),
      listInstituciones(),
      listComplejos(),
      listPisos(),
    ]);
    citas.value = citasData;
    pacientes.value = pacientesData;
    medicos.value = medicosData;
    consultorios.value = consultoriosData;
    instituciones.value = institucionesData;
    complejos.value = complejosData;
    pisos.value = pisosData;
    resetForm();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar citas.';
  }
}

async function submit(confirmarDuplicado = false) {
  error.value = '';
  message.value = '';
  if (!confirmarDuplicado) {
    duplicateWarning.value = null;
  }
  try {
    const { institucion_id: _institucionId, ...payload } = form;
    await createCita({ ...payload }, confirmarDuplicado);
    message.value = 'Cita creada.';
    duplicateWarning.value = null;
    resetForm();
    await load();
  } catch (err) {
    const duplicate = duplicateDetail(err);
    if (duplicate) {
      duplicateWarning.value = duplicate;
      return;
    }
    error.value = err instanceof Error ? err.message : 'No fue posible crear la cita.';
  }
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
          <label for="paciente">Paciente</label>
          <select id="paciente" v-model="form.paciente_id" required>
            <option v-for="paciente in pacientes" :key="paciente.id" :value="paciente.id">
              {{ paciente.nombre }} {{ paciente.apellido_paterno }} · {{ paciente.folio_paciente }}
            </option>
          </select>
        </div>
        <div class="form-row">
          <label for="medico">Médico</label>
          <select id="medico" v-model="form.medico_id" required>
            <option v-for="medico in medicos" :key="medico.id" :value="medico.id">
              {{ medico.nombre_visible || `${medico.nombre} ${medico.apellidos}` }}
            </option>
          </select>
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
          <label for="complejo">Complejo</label>
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
            <option v-for="piso in filteredPisos" :key="piso.id" :value="piso.nombre_visible" />
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
              :value="consultorio.nombre_visible || consultorio.codigo"
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
                {{ item.folio_turno }} · {{ item.estado }}
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
        <h2>Últimas citas</h2>
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
                <td><span class="status muted">{{ cita.estado }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>
</template>
