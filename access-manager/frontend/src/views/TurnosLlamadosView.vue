<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import {
  Complejo,
  Consultorio,
  getCurrentUser,
  Institucion,
  llamarCita,
  listAccessibleComplejos,
  listAccessibleConsultorios,
  listAccessibleInstituciones,
  listAccessibleMedicos,
  listAccessiblePisos,
  listAccessibleTorres,
  listTurnosDisplayRecientes,
  Medico,
  Piso,
  Torre,
  TurnoDisplayReciente,
  Usuario,
} from '../api/client';
import { pisoCodigoVisibleLabel, sortPisosByCodigo } from '../floorLabels';

const instituciones = ref<Institucion[]>([]);
const complejos = ref<Complejo[]>([]);
const torres = ref<Torre[]>([]);
const pisos = ref<Piso[]>([]);
const consultorios = ref<Consultorio[]>([]);
const medicos = ref<Medico[]>([]);
const currentUser = ref<Usuario | null>(null);
const rows = ref<TurnoDisplayReciente[]>([]);
const institucionId = ref('');
const complejoId = ref('');
const torreId = ref('');
const pisoId = ref('');
const clusterEsperaId = ref('');
const consultorioId = ref('');
const medicoId = ref('');
const minutos = ref(30);
const loading = ref(false);
const error = ref('');
const message = ref('');
const minuteOptions = Array.from({ length: 16 }, (_, index) => (index + 1) * 15);

const sortedInstituciones = computed(() => sortByLabel(instituciones.value, (item) => item.nombre));
const filteredComplejos = computed(() =>
  institucionId.value
    ? sortByLabel(
        complejos.value.filter((item) => item.institucion_id === institucionId.value),
        (item) => item.nombre,
      )
    : sortByLabel(complejos.value, (item) => item.nombre),
);

const filteredTorres = computed(() =>
  complejoId.value
    ? sortByLabel(
        torres.value.filter((item) => item.complejo_id === complejoId.value),
        (item) => item.nombre,
      )
    : [],
);

const filteredPisos = computed(() =>
  torreId.value ? sortPisosByCodigo(pisos.value.filter((item) => item.torre_id === torreId.value)) : [],
);

const filteredConsultorios = computed(() =>
  pisoId.value ? sortConsultoriosByCodigo(consultorios.value.filter((item) => item.piso_id === pisoId.value)) : [],
);

function pisoLabel(item: Piso) {
  return pisoCodigoVisibleLabel(item);
}

function consultorioLabel(item: Consultorio) {
  const visibleName = item.nombre_visible?.trim();
  return visibleName ? `${item.codigo} - ${visibleName}` : item.codigo;
}

function medicoLabel(item: Medico) {
  return item.nombre_visible || `${item.nombre} ${item.apellidos}`;
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

function defaultMedicoId() {
  const ownMedico = medicos.value.find((medico) => medico.usuario_id && medico.usuario_id === currentUser.value?.id);
  return ownMedico?.id ?? (medicos.value.length === 1 ? medicos.value[0].id : '');
}

function formatMinuteOption(value: number) {
  if (value < 60) return `${value} min`;
  const hours = Math.floor(value / 60);
  const minutes = value % 60;
  return minutes ? `${hours} h ${minutes} min` : `${hours} h`;
}

async function loadCatalogs() {
  const [userData, institucionesData, complejosData, torresData, pisosData, consultoriosData, medicosData] = await Promise.all([
    getCurrentUser(),
    listAccessibleInstituciones(),
    listAccessibleComplejos(),
    listAccessibleTorres(),
    listAccessiblePisos(),
    listAccessibleConsultorios(),
    listAccessibleMedicos(),
  ]);
  currentUser.value = userData;
  instituciones.value = institucionesData;
  complejos.value = complejosData;
  torres.value = torresData;
  pisos.value = pisosData;
  consultorios.value = consultoriosData;
  medicos.value = medicosData;
  medicoId.value ||= defaultMedicoId();
  prefillSingleAssignedLocation();
}

async function loadRows() {
  loading.value = true;
  error.value = '';
  try {
    rows.value = await listTurnosDisplayRecientes({
      institucion_id: institucionId.value,
      complejo_id: complejoId.value,
      torre_id: torreId.value,
      piso_id: pisoId.value,
      cluster_espera_id: clusterEsperaId.value,
      consultorio_id: consultorioId.value,
      medico_id: medicoId.value,
      minutos: minutos.value,
    });
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar los turnos llamados.';
  } finally {
    loading.value = false;
  }
}

function quickConsultorio() {
  const currentRows = filteredConsultorios.value;
  const scopedRows = sortConsultoriosByCodigo(
    consultorios.value.filter((item) => {
      if (complejoId.value && item.complejo_id !== complejoId.value) return false;
      if (torreId.value) {
        const piso = pisos.value.find((row) => row.id === item.piso_id);
        if (piso?.torre_id !== torreId.value) return false;
      }
      return true;
    }),
  );
  const selected = currentRows.find((item) => item.id === consultorioId.value) ?? currentRows[0] ?? scopedRows[0] ?? null;
  if (selected) {
    setLocationFromConsultorio(selected);
  }
  void loadRows();
}

function quickPiso() {
  const selectedConsultorio = consultorios.value.find((item) => item.id === consultorioId.value);
  pisoId.value ||= selectedConsultorio?.piso_id ?? filteredPisos.value[0]?.id ?? '';
  const selectedPiso = pisos.value.find((item) => item.id === pisoId.value);
  if (selectedPiso) {
    setLocationFromPiso(selectedPiso);
  }
  if (!filteredConsultorios.value.some((item) => item.id === consultorioId.value)) {
    consultorioId.value = '';
  }
  void loadRows();
}

function quickCluster() {
  clusterEsperaId.value ||= '';
  void loadRows();
}

function formatTime(value: string) {
  return new Date(value).toLocaleTimeString();
}

function displayText(item: TurnoDisplayReciente) {
  return item.texto || `Turno ${item.turno} a consultorio ${item.consultorio}`;
}

function statusLabel(status: string | null | undefined) {
  if (!status) return 'Sin estado';
  if (status === 'NO_LLEGO') return 'No Se Presentó';
  return status;
}

function canCallAgain(item: TurnoDisplayReciente) {
  if (!item.cita_id) return false;
  if ((item.llamado_numero ?? 1) >= 3) return false;
  return !['CANCELADA', 'EXPIRADA', 'FINALIZADA', 'NO_LLEGO'].includes(item.estado_cita ?? '');
}

async function callAgain(item: TurnoDisplayReciente) {
  if (!item.cita_id) return;
  loading.value = true;
  error.value = '';
  message.value = '';
  try {
    const response = await llamarCita(item.cita_id);
    message.value = response.llamado_numero >= 3 ? 'Tercer llamado registrado. La cita quedó como No Se Presentó.' : 'Turno llamado.';
    await loadRows();
  } catch (err) {
    const failure = err instanceof Error ? err.message : 'No fue posible llamar el turno.';
    await loadRows();
    error.value = failure;
  } finally {
    loading.value = false;
  }
}

function onInstitutionChange() {
  if (!filteredComplejos.value.some((item) => item.id === complejoId.value)) {
    complejoId.value = '';
  }
  torreId.value = '';
  pisoId.value = '';
  consultorioId.value = '';
  clusterEsperaId.value = '';
  void loadRows();
}

function onComplejoChange() {
  const selected = complejos.value.find((item) => item.id === complejoId.value);
  institucionId.value = selected?.institucion_id ?? institucionId.value;
  torreId.value = '';
  pisoId.value = '';
  consultorioId.value = '';
  clusterEsperaId.value = '';
  void loadRows();
}

function onTorreChange() {
  if (!filteredPisos.value.some((item) => item.id === pisoId.value)) {
    pisoId.value = '';
  }
  consultorioId.value = '';
  clusterEsperaId.value = '';
  void loadRows();
}

function onPisoChange() {
  if (!filteredConsultorios.value.some((item) => item.id === consultorioId.value)) {
    consultorioId.value = '';
  }
  void loadRows();
}

function setLocationFromPiso(piso: Piso) {
  torreId.value = piso.torre_id;
  const selectedTorre = torres.value.find((item) => item.id === piso.torre_id);
  if (!selectedTorre) return;
  complejoId.value = selectedTorre.complejo_id;
  institucionId.value = complejos.value.find((item) => item.id === selectedTorre.complejo_id)?.institucion_id ?? institucionId.value;
}

function setLocationFromConsultorio(consultorio: Consultorio) {
  const piso = pisos.value.find((item) => item.id === consultorio.piso_id);
  if (piso) {
    pisoId.value = piso.id;
    setLocationFromPiso(piso);
  }
  consultorioId.value = consultorio.id;
}

function prefillSingleAssignedLocation() {
  const singleConsultorio = consultorios.value.length === 1 ? consultorios.value[0] : null;
  const singlePiso = pisos.value.length === 1 ? pisos.value[0] : null;
  const basePiso = singleConsultorio ? pisos.value.find((item) => item.id === singleConsultorio.piso_id) ?? null : singlePiso;
  if (!basePiso || torreId.value) return;
  const torre = torres.value.find((item) => item.id === basePiso.torre_id);
  if (!torre) return;
  torreId.value = torre.id;
  if (!complejoId.value) {
    complejoId.value = torre.complejo_id;
  }
  const complejo = complejos.value.find((item) => item.id === torre.complejo_id);
  if (complejo && !institucionId.value) {
    institucionId.value = complejo.institucion_id;
  }
}

onMounted(async () => {
  await loadCatalogs();
  await loadRows();
});
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Turnos llamados</h1>
        <p>Consulta rápida para resolver dudas de pacientes en recepción, operación y consultorio.</p>
      </div>
      <button class="secondary" type="button" @click="loadRows">Actualizar</button>
    </header>

    <section class="panel form">
      <div class="form-grid">
        <div class="form-row">
          <label for="institucion-turnos">Institución</label>
          <select id="institucion-turnos" v-model="institucionId" @change="onInstitutionChange">
            <option value="">Todas</option>
            <option v-for="item in sortedInstituciones" :key="item.id" :value="item.id">{{ item.nombre }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="complejo-turnos">Campus</label>
          <select id="complejo-turnos" v-model="complejoId" @change="onComplejoChange">
            <option value="">Todos</option>
            <option v-for="item in filteredComplejos" :key="item.id" :value="item.id">{{ item.nombre }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="torre-turnos">Torre</label>
          <select id="torre-turnos" v-model="torreId" :disabled="!complejoId" @change="onTorreChange">
            <option value="">Todas</option>
            <option v-for="item in filteredTorres" :key="item.id" :value="item.id">{{ item.nombre }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="piso-turnos">Piso</label>
          <select id="piso-turnos" v-model="pisoId" :disabled="!torreId" @change="onPisoChange">
            <option value="">Todos</option>
            <option v-for="item in filteredPisos" :key="item.id" :value="item.id">{{ pisoLabel(item) }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="consultorio-turnos">Consultorio</label>
          <select id="consultorio-turnos" v-model="consultorioId" :disabled="!pisoId" @change="loadRows">
            <option value="">Todos</option>
            <option v-for="item in filteredConsultorios" :key="item.id" :value="item.id">{{ consultorioLabel(item) }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="medico-turnos">Médico</label>
          <select id="medico-turnos" v-model="medicoId" @change="loadRows">
            <option value="">Todos</option>
            <option v-for="item in medicos" :key="item.id" :value="item.id">{{ medicoLabel(item) }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="cluster-turnos">Clúster</label>
          <input id="cluster-turnos" v-model="clusterEsperaId" placeholder="UUID de clúster" @change="loadRows" />
        </div>
        <div class="form-row">
          <label for="minutos-turnos">Minutos</label>
          <select id="minutos-turnos" v-model.number="minutos" @change="loadRows">
            <option v-for="option in minuteOptions" :key="option" :value="option">{{ formatMinuteOption(option) }}</option>
          </select>
        </div>
      </div>
      <div class="actions-row">
        <button class="secondary" type="button" @click="quickConsultorio">Mi consultorio</button>
        <button class="secondary" type="button" @click="quickPiso">Mi piso</button>
        <button class="secondary" type="button" @click="quickCluster">Mi clúster</button>
      </div>
    </section>

    <p v-if="message" class="message">{{ message }}</p>
    <p v-if="error" class="error">{{ error }}</p>

    <section class="panel">
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Turno</th>
              <th>Texto en pantalla</th>
              <th>Llamados</th>
              <th>Hora llamado</th>
              <th>Estado cita</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in rows" :key="`${item.turno}-${item.llamado_en}`">
              <td><strong>{{ item.turno }}</strong></td>
              <td>{{ displayText(item) }}</td>
              <td>{{ item.llamado_numero ?? 1 }}/3</td>
              <td>{{ formatTime(item.llamado_en) }}</td>
              <td><span class="status ok">{{ statusLabel(item.estado_cita || item.estado) }}</span></td>
              <td>
                <button class="small secondary" type="button" :disabled="!canCallAgain(item) || loading" @click="callAgain(item)">
                  Llamar
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="!loading && rows.length === 0" class="message">No hay turnos llamados en el periodo seleccionado.</p>
    </section>
  </section>
</template>
