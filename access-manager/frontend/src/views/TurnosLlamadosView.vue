<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import {
  Complejo,
  Consultorio,
  Institucion,
  llamarCita,
  listComplejos,
  listConsultorios,
  listInstituciones,
  listPisos,
  listTurnosDisplayRecientes,
  Piso,
  TurnoDisplayReciente,
} from '../api/client';

const instituciones = ref<Institucion[]>([]);
const complejos = ref<Complejo[]>([]);
const pisos = ref<Piso[]>([]);
const consultorios = ref<Consultorio[]>([]);
const rows = ref<TurnoDisplayReciente[]>([]);
const institucionId = ref('');
const complejoId = ref('');
const pisoId = ref('');
const clusterEsperaId = ref('');
const consultorioId = ref('');
const minutos = ref(30);
const loading = ref(false);
const error = ref('');
const message = ref('');
const minuteOptions = Array.from({ length: 16 }, (_, index) => (index + 1) * 15);

const filteredComplejos = computed(() =>
  institucionId.value ? complejos.value.filter((item) => item.institucion_id === institucionId.value) : complejos.value,
);

const filteredPisos = computed(() => (complejoId.value ? pisos.value.filter((item) => item.complejo_id === complejoId.value) : []));

const filteredConsultorios = computed(() =>
  consultorios.value.filter((item) => {
    if (!complejoId.value || item.complejo_id !== complejoId.value) return false;
    if (pisoId.value && item.piso_id !== pisoId.value) return false;
    return true;
  }),
);

function formatMinuteOption(value: number) {
  if (value < 60) return `${value} min`;
  const hours = Math.floor(value / 60);
  const minutes = value % 60;
  return minutes ? `${hours} h ${minutes} min` : `${hours} h`;
}

async function loadCatalogs() {
  const [institucionesData, complejosData, pisosData, consultoriosData] = await Promise.all([
    listInstituciones(),
    listComplejos(),
    listPisos(),
    listConsultorios(),
  ]);
  instituciones.value = institucionesData;
  complejos.value = complejosData;
  pisos.value = pisosData;
  consultorios.value = consultoriosData;
  institucionId.value ||= complejosData[0]?.institucion_id ?? institucionesData[0]?.id ?? '';
  complejoId.value ||= filteredComplejos.value[0]?.id ?? complejosData[0]?.id ?? '';
}

async function loadRows() {
  if (!complejoId.value) {
    rows.value = [];
    error.value = '';
    return;
  }
  loading.value = true;
  error.value = '';
  try {
    rows.value = await listTurnosDisplayRecientes({
      complejo_id: complejoId.value,
      piso_id: pisoId.value,
      cluster_espera_id: clusterEsperaId.value,
      consultorio_id: consultorioId.value,
      minutos: minutos.value,
    });
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar los turnos llamados.';
  } finally {
    loading.value = false;
  }
}

function quickConsultorio() {
  consultorioId.value ||= filteredConsultorios.value[0]?.id ?? '';
  void loadRows();
}

function quickPiso() {
  const selectedConsultorio = consultorios.value.find((item) => item.id === consultorioId.value);
  pisoId.value ||= selectedConsultorio?.piso_id ?? filteredPisos.value[0]?.id ?? '';
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
    complejoId.value = filteredComplejos.value[0]?.id ?? '';
  }
  pisoId.value = '';
  consultorioId.value = '';
  clusterEsperaId.value = '';
  void loadRows();
}

function onComplejoChange() {
  const selected = complejos.value.find((item) => item.id === complejoId.value);
  institucionId.value = selected?.institucion_id ?? institucionId.value;
  pisoId.value = '';
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
            <option v-for="item in instituciones" :key="item.id" :value="item.id">{{ item.nombre }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="complejo-turnos">Complejo</label>
          <select id="complejo-turnos" v-model="complejoId" @change="onComplejoChange">
            <option value="">Selecciona un complejo</option>
            <option v-for="item in filteredComplejos" :key="item.id" :value="item.id">{{ item.nombre }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="piso-turnos">Piso</label>
          <select id="piso-turnos" v-model="pisoId" :disabled="!complejoId" @change="onPisoChange">
            <option value="">Todos</option>
            <option v-for="item in filteredPisos" :key="item.id" :value="item.id">{{ item.nombre_visible }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="consultorio-turnos">Consultorio</label>
          <select id="consultorio-turnos" v-model="consultorioId" :disabled="!complejoId" @change="loadRows">
            <option value="">Todos</option>
            <option v-for="item in filteredConsultorios" :key="item.id" :value="item.id">{{ item.nombre_visible || item.codigo }}</option>
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
