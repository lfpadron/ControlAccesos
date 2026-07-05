<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import QRCode from 'qrcode';
import {
  auditCitasExport,
  autorizarPasar,
  cancelarCita,
  checkinLobby,
  generarQr,
  getTicket,
  llamarCita,
  listCitasHoy,
  listComplejos,
  listConsultorios,
  listInstituciones,
  listMedicos,
  listPisos,
  type Cita,
  type CitaFilters,
  type Complejo,
  type Consultorio,
  type Institucion,
  type Medico,
  type Piso,
  type TicketResponse,
} from '../api/client';
import { todayLocalIso } from '../dateUtils';
import { exportRows, type ExportFormat } from '../exporters';

const citas = ref<Cita[]>([]);
const instituciones = ref<Institucion[]>([]);
const complejos = ref<Complejo[]>([]);
const pisos = ref<Piso[]>([]);
const consultorios = ref<Consultorio[]>([]);
const medicos = ref<Medico[]>([]);
const error = ref('');
const message = ref('');
const qrPayload = ref('');
const qrDataUrl = ref('');
const ticket = ref<TicketResponse | null>(null);
const selectedCita = ref<Cita | null>(null);
const selectedSlot = ref('');
const loading = ref(false);
const institucionSearch = ref('');
const complejoSearch = ref('');
const pisoSearch = ref('');
const consultorioSearch = ref('');

const filters = reactive({
  fecha: todayLocalIso(),
  estado: '',
  institucion_id: '',
  complejo_id: '',
  piso_id: '',
  consultorio_id: '',
  medico_id: '',
  paciente: '',
});

const filteredComplejos = computed(() =>
  filters.institucion_id ? complejos.value.filter((item) => item.institucion_id === filters.institucion_id) : complejos.value,
);
const filteredPisos = computed(() => (filters.complejo_id ? pisos.value.filter((item) => item.complejo_id === filters.complejo_id) : pisos.value));
const filteredConsultorios = computed(() =>
  consultorios.value.filter((item) => {
    if (filters.complejo_id && item.complejo_id !== filters.complejo_id) return false;
    if (filters.piso_id && item.piso_id !== filters.piso_id) return false;
    return true;
  }),
);

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

function syncInstitution() {
  filters.institucion_id = matchByLabel(instituciones.value, institucionSearch.value, institucionLabel)?.id ?? '';
  if (!filteredComplejos.value.some((item) => item.id === filters.complejo_id)) {
    filters.complejo_id = '';
    complejoSearch.value = '';
    filters.piso_id = '';
    pisoSearch.value = '';
    filters.consultorio_id = '';
    consultorioSearch.value = '';
  }
}

function syncComplex() {
  filters.complejo_id = matchByLabel(filteredComplejos.value, complejoSearch.value, (item) => item.nombre)?.id ?? '';
  if (!filteredPisos.value.some((item) => item.id === filters.piso_id)) {
    filters.piso_id = '';
    pisoSearch.value = '';
    filters.consultorio_id = '';
    consultorioSearch.value = '';
  }
}

function syncPiso() {
  filters.piso_id = matchByLabel(filteredPisos.value, pisoSearch.value, (item) => item.nombre_visible)?.id ?? '';
  if (!filteredConsultorios.value.some((item) => item.id === filters.consultorio_id)) {
    filters.consultorio_id = '';
    consultorioSearch.value = '';
  }
}

function syncConsultorio() {
  filters.consultorio_id = matchByLabel(filteredConsultorios.value, consultorioSearch.value, (item) => item.nombre_visible || item.codigo)?.id ?? '';
}

function requestFilters(): CitaFilters {
  return {
    fecha: filters.fecha,
    estado: filters.estado,
    complejo_id: filters.complejo_id,
    piso_id: filters.piso_id,
    consultorio_id: filters.consultorio_id,
    medico_id: filters.medico_id,
    paciente: filters.paciente.trim(),
  };
}

function slotKey(hora: string) {
  const [hourText, minuteText] = hora.split(':');
  const hour = Number(hourText);
  const minute = Number(minuteText);
  const slotMinute = minute < 30 ? 0 : 30;
  return `${String(hour).padStart(2, '0')}:${String(slotMinute).padStart(2, '0')}`;
}

function slotEnd(slot: string) {
  const [hourText, minuteText] = slot.split(':');
  const date = new Date(2000, 0, 1, Number(hourText), Number(minuteText) + 30);
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
}

const slots = computed(() => [...new Set(citas.value.map((cita) => slotKey(cita.hora_cita)))].sort());
const slotRows = computed(() => citas.value.filter((cita) => slotKey(cita.hora_cita) === selectedSlot.value));
const currentSlotIndex = computed(() => slots.value.findIndex((slot) => slot === selectedSlot.value));

async function load() {
  loading.value = true;
  error.value = '';
  try {
    citas.value = await listCitasHoy(requestFilters());
    if (!slots.value.includes(selectedSlot.value)) {
      selectedSlot.value = slots.value[0] ?? '';
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar las citas.';
  } finally {
    loading.value = false;
  }
}

async function loadCatalogs() {
  try {
    const [institucionesData, complejosData, pisosData, consultoriosData, medicosData] = await Promise.all([
      listInstituciones(),
      listComplejos(),
      listPisos(),
      listConsultorios(),
      listMedicos(),
    ]);
    instituciones.value = institucionesData;
    complejos.value = complejosData;
    pisos.value = pisosData;
    consultorios.value = consultoriosData;
    medicos.value = medicosData;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar filtros.';
  }
}

async function run(action: () => Promise<unknown>, success: string) {
  error.value = '';
  message.value = '';
  try {
    await action();
    message.value = success;
    await load();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible completar la acción.';
  }
}

function statusLabel(status: string) {
  if (status === 'NO_LLEGO') return 'No Se Presentó';
  return status;
}

function canCall(cita: Cita) {
  return !['CANCELADA', 'EXPIRADA', 'FINALIZADA', 'NO_LLEGO'].includes(cita.estado);
}

async function callCita(cita: Cita) {
  error.value = '';
  message.value = '';
  try {
    const response = await llamarCita(cita.id);
    message.value = response.llamado_numero >= 3 ? 'Tercer llamado registrado. La cita quedó como No Se Presentó.' : 'Turno llamado.';
    await load();
  } catch (err) {
    const failure = err instanceof Error ? err.message : 'No fue posible llamar el turno.';
    await load();
    error.value = failure;
  }
}

function fileNameFor(cita: Cita | null) {
  if (!cita) return 'turno_qr.png';
  const hora = cita.hora_cita.slice(0, 5).replace(':', '-');
  return `${cita.folio_turno}_${cita.fecha_cita}_${hora}.png`;
}

function downloadQr() {
  if (!qrDataUrl.value) return;
  const link = document.createElement('a');
  link.href = qrDataUrl.value;
  link.download = fileNameFor(selectedCita.value);
  link.click();
}

async function renderQr(payload: string) {
  qrDataUrl.value = await QRCode.toDataURL(payload, { margin: 2, width: 240 });
}

async function showQr(cita: Cita) {
  error.value = '';
  message.value = '';
  try {
    const qr = await generarQr(cita.id);
    qrPayload.value = qr.qr_payload;
    selectedCita.value = cita;
    await renderQr(qr.qr_payload);
    ticket.value = null;
    message.value = 'QR generado.';
    await load();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible generar el QR.';
  }
}

async function showTicket(cita: Cita) {
  error.value = '';
  message.value = '';
  try {
    ticket.value = await getTicket(cita.id);
    selectedCita.value = cita;
    qrPayload.value = '';
    await renderQr(ticket.value.qr_payload);
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible generar el ticket.';
  }
}

function previousSlot() {
  const index = currentSlotIndex.value;
  if (index > 0) selectedSlot.value = slots.value[index - 1];
}

function nextSlot() {
  const index = currentSlotIndex.value;
  if (index >= 0 && index < slots.value.length - 1) selectedSlot.value = slots.value[index + 1];
}

function clearFilters() {
  filters.fecha = todayLocalIso();
  filters.estado = '';
  filters.institucion_id = '';
  filters.complejo_id = '';
  filters.piso_id = '';
  filters.consultorio_id = '';
  filters.medico_id = '';
  filters.paciente = '';
  institucionSearch.value = '';
  complejoSearch.value = '';
  pisoSearch.value = '';
  consultorioSearch.value = '';
  void load();
}

function patientMedicalDisplay(cita: Cita) {
  return cita.paciente_nombre_completo || cita.paciente || cita.paciente_id;
}

const exportColumns = [
  { key: 'fecha_cita', label: 'Fecha' },
  { key: 'hora_cita', label: 'Hora', value: (row: Cita) => row.hora_cita.slice(0, 5) },
  { key: 'folio_turno', label: 'Turno' },
  { key: 'paciente_nombre_completo', label: 'Paciente', value: patientMedicalDisplay },
  { key: 'medico', label: 'Médico' },
  { key: 'consultorio', label: 'Consultorio' },
  { key: 'piso', label: 'Piso' },
  { key: 'estado', label: 'Estado' },
  { key: 'tipo', label: 'Tipo' },
];

async function exportCitas(format: ExportFormat) {
  error.value = '';
  try {
    await auditCitasExport({ ...requestFilters(), formato: format });
    exportRows(citas.value, exportColumns, `citas-${filters.fecha}`, format);
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible exportar citas.';
  }
}

onMounted(async () => {
  await loadCatalogs();
  await load();
});
</script>

<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1>Citas de hoy</h1>
        <p>Operación diaria por fecha, estado, ubicación y paciente.</p>
      </div>
      <button class="secondary" type="button" @click="load">Actualizar</button>
    </div>

    <form class="panel form" @submit.prevent="load">
      <div class="form-grid">
        <div class="form-row">
          <label for="filtro-fecha">Fecha</label>
          <input id="filtro-fecha" v-model="filters.fecha" type="date" required />
        </div>
        <div class="form-row">
          <label for="filtro-estado">Estado</label>
          <select id="filtro-estado" v-model="filters.estado">
            <option value="">Todos</option>
            <option value="AGENDADA">Agendada</option>
            <option value="QR_GENERADO">QR generado</option>
            <option value="LLEGO_LOBBY">Llegó lobby</option>
            <option value="AUTORIZADO_PASAR">Autorizado</option>
            <option value="EN_CONSULTA">En consulta</option>
            <option value="FINALIZADA">Finalizada</option>
            <option value="NO_LLEGO">No Se Presentó</option>
            <option value="CANCELADA">Cancelada</option>
            <option value="EXPIRADA">Expirada</option>
          </select>
        </div>
        <div class="form-row">
          <label for="filtro-institucion">Institución</label>
          <input id="filtro-institucion" v-model="institucionSearch" list="filtro-instituciones" @input="syncInstitution" @change="syncInstitution" />
          <datalist id="filtro-instituciones">
            <option v-for="item in instituciones" :key="item.id" :value="institucionLabel(item)" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="filtro-complejo">Complejo</label>
          <input id="filtro-complejo" v-model="complejoSearch" list="filtro-complejos" @input="syncComplex" @change="syncComplex" />
          <datalist id="filtro-complejos">
            <option v-for="item in filteredComplejos" :key="item.id" :value="item.nombre" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="filtro-piso">Piso</label>
          <input id="filtro-piso" v-model="pisoSearch" list="filtro-pisos" @input="syncPiso" @change="syncPiso" />
          <datalist id="filtro-pisos">
            <option v-for="item in filteredPisos" :key="item.id" :value="item.nombre_visible" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="filtro-consultorio">Consultorio</label>
          <input id="filtro-consultorio" v-model="consultorioSearch" list="filtro-consultorios" @input="syncConsultorio" @change="syncConsultorio" />
          <datalist id="filtro-consultorios">
            <option v-for="item in filteredConsultorios" :key="item.id" :value="item.nombre_visible || item.codigo" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="filtro-medico">Médico</label>
          <select id="filtro-medico" v-model="filters.medico_id">
            <option value="">Todos</option>
            <option v-for="medico in medicos" :key="medico.id" :value="medico.id">
              {{ medico.nombre_visible || `${medico.nombre} ${medico.apellidos}` }}
            </option>
          </select>
        </div>
        <div class="form-row">
          <label for="filtro-paciente">Paciente</label>
          <input id="filtro-paciente" v-model="filters.paciente" placeholder="Nombre del paciente" />
        </div>
      </div>
      <div class="actions-row">
        <button type="submit" :disabled="loading">Filtrar</button>
        <button class="secondary" type="button" @click="clearFilters">Limpiar</button>
        <button class="secondary" type="button" @click="exportCitas('excel')">Excel</button>
        <button class="secondary" type="button" @click="exportCitas('csv')">CSV</button>
        <button class="secondary" type="button" @click="exportCitas('json')">JSON</button>
      </div>
    </form>

    <div class="panel table-panel">
      <div class="page-header compact">
        <div>
          <h2>{{ citas.length }} citas</h2>
          <p v-if="selectedSlot">{{ selectedSlot }} - {{ slotEnd(selectedSlot) }} · {{ slotRows.length }} registros</p>
          <p v-else>Sin intervalos para mostrar</p>
        </div>
        <div class="inline-actions">
          <button class="secondary" type="button" :disabled="currentSlotIndex <= 0" @click="previousSlot">Anterior</button>
          <button class="secondary" type="button" :disabled="currentSlotIndex < 0 || currentSlotIndex >= slots.length - 1" @click="nextSlot">Siguiente</button>
        </div>
      </div>
      <p v-if="message" class="message">{{ message }}</p>
      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="loading" class="message">Cargando...</p>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Hora</th>
              <th>Turno</th>
              <th>Paciente</th>
              <th>Médico</th>
              <th>Consultorio</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="cita in slotRows" :key="cita.id">
              <td>{{ cita.hora_cita.slice(0, 5) }}</td>
              <td><strong>{{ cita.folio_turno }}</strong></td>
              <td>{{ patientMedicalDisplay(cita) }}</td>
              <td>{{ cita.medico || cita.medico_id }}</td>
              <td>{{ cita.consultorio || cita.consultorio_id }}</td>
              <td><span class="status muted">{{ statusLabel(cita.estado) }}</span></td>
              <td>
                <div class="inline-actions">
                  <button class="small" type="button" @click="showQr(cita)">QR</button>
                  <button class="small secondary" type="button" @click="showTicket(cita)">Ticket</button>
                  <button class="small secondary" type="button" @click="run(() => checkinLobby(cita.id), 'Check-in registrado.')">Check-in</button>
                  <button class="small secondary" type="button" @click="run(() => autorizarPasar(cita.id), 'Acceso autorizado.')">Autorizar</button>
                  <button class="small" type="button" :disabled="!canCall(cita) || loading" @click="callCita(cita)">Llamar</button>
                  <button class="small danger" type="button" @click="run(() => cancelarCita(cita.id), 'Cita cancelada.')">Cancelar</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="!loading && citas.length === 0" class="message">No hay citas con estos filtros.</p>
    </div>

    <div v-if="qrPayload || ticket" class="panel">
      <h2>{{ ticket ? 'Ticket lógico' : 'QR generado' }}</h2>
      <div class="qr-preview">
        <img v-if="qrDataUrl" :src="qrDataUrl" alt="QR de la cita" />
        <button class="secondary" type="button" @click="downloadQr">Bajar</button>
      </div>
      <pre v-if="ticket">{{ ticket.encabezado_fecha }}
{{ ticket.leyenda }}

Turno {{ ticket.turno }}

[QR]

Consultorio {{ ticket.consultorio }}
{{ ticket.piso }}
Cita {{ ticket.hora }} hrs</pre>
      <p v-else class="message">QR listo para descargar o presentar en kiosko.</p>
    </div>
  </section>
</template>
