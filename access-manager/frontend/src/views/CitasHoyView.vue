<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import QRCode from 'qrcode';
import {
  auditCitasExport,
  autorizarPasar,
  cancelarCita,
  checkinLobby,
  generarQr,
  getCurrentUser,
  getTicket,
  llamarCita,
  listAccessibleComplejos,
  listAccessibleConsultorios,
  listAccessibleInstituciones,
  listAccessibleMedicos,
  listAccessiblePisos,
  listAccessibleTorres,
  listCitasHoy,
  type Cita,
  type CitaFilters,
  type Complejo,
  type Consultorio,
  type Institucion,
  type Medico,
  type Piso,
  type TicketResponse,
  type Torre,
  type Usuario,
} from '../api/client';
import { localTimeMinusHours, localTimePlusHours, todayLocalIso } from '../dateUtils';
import { exportRows } from '../exporters';
import { pisoCodigoVisibleLabel, sortPisosByCodigo } from '../floorLabels';

const citas = ref<Cita[]>([]);
const instituciones = ref<Institucion[]>([]);
const complejos = ref<Complejo[]>([]);
const torres = ref<Torre[]>([]);
const pisos = ref<Piso[]>([]);
const consultorios = ref<Consultorio[]>([]);
const medicos = ref<Medico[]>([]);
const currentUser = ref<Usuario | null>(null);
const error = ref('');
const message = ref('');
const qrPayload = ref('');
const qrDataUrl = ref('');
const ticket = ref<TicketResponse | null>(null);
const selectedCita = ref<Cita | null>(null);
const selectedDoctorStatusCita = ref<Cita | null>(null);
const loading = ref(false);

const filters = reactive({
  fecha: todayLocalIso(),
  hora_inicio: localTimeMinusHours(1),
  hora_fin: localTimePlusHours(1),
  estado: '',
  institucion_id: '',
  complejo_id: '',
  torre_id: '',
  piso_id: '',
  consultorio_id: '',
  medico_id: '',
  paciente: '',
});

const sortedInstituciones = computed(() => sortByLabel(instituciones.value, institucionLabel));
const filteredComplejos = computed(() =>
  filters.institucion_id
    ? sortByLabel(
        complejos.value.filter((item) => item.institucion_id === filters.institucion_id),
        (item) => item.nombre,
      )
    : [],
);
const filteredTorres = computed(() =>
  filters.complejo_id
    ? sortByLabel(
        torres.value.filter((item) => item.complejo_id === filters.complejo_id),
        (item) => item.nombre,
      )
    : [],
);
const filteredPisos = computed(() =>
  filters.torre_id ? sortPisosByCodigo(pisos.value.filter((item) => item.torre_id === filters.torre_id)) : [],
);
const filteredConsultorios = computed(() =>
  filters.piso_id ? sortConsultoriosByCodigo(consultorios.value.filter((item) => item.piso_id === filters.piso_id)) : [],
);

function institucionLabel(item: Institucion) {
  return item.nombre;
}

function pisoLabel(item: Piso) {
  return pisoCodigoVisibleLabel(item);
}

function medicoLabel(item: Medico) {
  return item.nombre_visible || `${item.nombre} ${item.apellidos}`;
}

function consultorioLabel(item: Consultorio) {
  const visibleName = item.nombre_visible?.trim();
  return visibleName ? `${item.codigo} - ${visibleName}` : item.codigo;
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

function onInstitucionChange() {
  if (!filteredComplejos.value.some((item) => item.id === filters.complejo_id)) {
    filters.complejo_id = '';
  }
  filters.torre_id = '';
  filters.piso_id = '';
  filters.consultorio_id = '';
}

function onComplejoChange() {
  if (!filteredTorres.value.some((item) => item.id === filters.torre_id)) {
    filters.torre_id = '';
  }
  filters.piso_id = '';
  filters.consultorio_id = '';
}

function onTorreChange() {
  if (!filteredPisos.value.some((item) => item.id === filters.piso_id)) {
    filters.piso_id = '';
  }
  filters.consultorio_id = '';
}

function onPisoChange() {
  if (!filteredConsultorios.value.some((item) => item.id === filters.consultorio_id)) {
    filters.consultorio_id = '';
  }
}

function defaultMedicoId() {
  const ownMedico = medicos.value.find((medico) => medico.usuario_id && medico.usuario_id === currentUser.value?.id);
  return ownMedico?.id ?? (medicos.value.length === 1 ? medicos.value[0].id : '');
}

function requestFilters(): CitaFilters {
  return {
    fecha: filters.fecha,
    hora_inicio: filters.hora_inicio,
    hora_fin: filters.hora_fin,
    estado: filters.estado,
    institucion_id: filters.institucion_id,
    complejo_id: filters.complejo_id,
    torre_id: filters.torre_id,
    piso_id: filters.piso_id,
    consultorio_id: filters.consultorio_id,
    medico_id: filters.medico_id,
    paciente: filters.paciente.trim(),
  };
}

const timeRangeLabel = computed(() => {
  if (filters.hora_inicio && filters.hora_fin) return `${filters.hora_inicio} - ${filters.hora_fin}`;
  if (filters.hora_inicio) return `Desde ${filters.hora_inicio}`;
  if (filters.hora_fin) return `Hasta ${filters.hora_fin}`;
  return 'Todo el día';
});

const doctorStatusOptions = [
  { value: 'AUSENTE', label: 'Ausente', tone: 'red', icon: 'x' },
  { value: 'NO_DISPONIBLE', label: 'No disponible', tone: 'orange', icon: '!' },
  { value: 'EN_CONSULTA', label: 'En consulta', tone: 'yellow', icon: '' },
  { value: 'DISPONIBLE', label: 'Disponible', tone: 'green', icon: '✓' },
  { value: 'NO_MOSTRAR', label: 'No mostrar', tone: 'muted', icon: '' },
];

async function load() {
  loading.value = true;
  error.value = '';
  try {
    citas.value = await listCitasHoy(requestFilters());
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar las citas.';
  } finally {
    loading.value = false;
  }
}

async function loadCatalogs() {
  try {
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
    filters.medico_id ||= defaultMedicoId();
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

function shortDateTime(value?: string | null) {
  if (!value) return '-';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value.replace('T', ' ').slice(0, 16);
  return new Intl.DateTimeFormat('es-MX', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(parsed);
}

function checkinTypeLabel(value?: string | null) {
  const labels: Record<string, string> = {
    LECTOR_QR_APP: 'Lector QR app',
    KIOSKO: 'Kiosko',
    RECEPCION_MANUAL: 'Recepción manual',
    RECEPCION_QR: 'Recepción QR',
  };
  return value ? labels[value] ?? value : '-';
}

function cancelTypeLabel(value?: string | null) {
  const labels: Record<string, string> = {
    MANUAL: 'Manual',
    SISTEMA: 'Sistema',
  };
  return value ? labels[value] ?? value : '-';
}

function statusLabel(status: string) {
  if (status === 'NO_LLEGO') return 'No Se Presentó';
  return status;
}

function doctorStatusLabel(status: string) {
  return doctorStatusOptions.find((item) => item.value === status)?.label ?? status;
}

function doctorStatusTone(status: string) {
  return doctorStatusOptions.find((item) => item.value === status)?.tone ?? 'muted';
}

function doctorStatusIcon(status: string) {
  return doctorStatusOptions.find((item) => item.value === status)?.icon ?? '';
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

function clearFilters() {
  filters.fecha = todayLocalIso();
  filters.hora_inicio = localTimeMinusHours(1);
  filters.hora_fin = localTimePlusHours(1);
  filters.estado = '';
  filters.institucion_id = '';
  filters.complejo_id = '';
  filters.torre_id = '';
  filters.piso_id = '';
  filters.consultorio_id = '';
  filters.medico_id = defaultMedicoId();
  filters.paciente = '';
  void load();
}

function patientMedicalDisplay(cita: Cita) {
  return cita.paciente_nombre_completo || cita.paciente || cita.paciente_id;
}

function showDoctorStatusDialog(cita: Cita) {
  selectedDoctorStatusCita.value = cita;
}

const exportColumns = [
  { key: 'fecha_cita', label: 'Fecha' },
  { key: 'hora_cita', label: 'Hora', value: (row: Cita) => row.hora_cita.slice(0, 5) },
  { key: 'folio_turno', label: 'Turno' },
  { key: 'paciente_nombre_completo', label: 'Paciente', value: patientMedicalDisplay },
  { key: 'medico', label: 'Médico' },
  { key: 'medico_estado_atencion', label: 'Estado médico', value: (row: Cita) => doctorStatusLabel(row.medico_estado_atencion) },
  { key: 'consultorio', label: 'Consultorio' },
  { key: 'piso', label: 'Piso' },
  { key: 'estado', label: 'Estado' },
  { key: 'tipo', label: 'Tipo' },
  { key: 'fecha_hora_checkin', label: 'Check-in', value: (row: Cita) => shortDateTime(row.fecha_hora_checkin) },
  { key: 'tipo_checkin', label: 'Tipo check-in', value: (row: Cita) => checkinTypeLabel(row.tipo_checkin) },
  { key: 'usuario_checkin_id', label: 'Usuario check-in' },
  { key: 'fecha_hora_autorizar', label: 'Autorización', value: (row: Cita) => shortDateTime(row.fecha_hora_autorizar) },
  { key: 'fecha_hora_llamar', label: 'Llamado', value: (row: Cita) => shortDateTime(row.fecha_hora_llamar) },
  { key: 'fecha_hora_cancelar', label: 'Cancelación', value: (row: Cita) => shortDateTime(row.fecha_hora_cancelar) },
  { key: 'tipo_cancelacion', label: 'Tipo cancelación', value: (row: Cita) => cancelTypeLabel(row.tipo_cancelacion) },
  { key: 'usuario_cancelacion_id', label: 'Usuario cancelación' },
];

async function exportCitas(format: 'excel' | 'csv' | 'json') {
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
          <label for="filtro-hora-inicio">Hora inicio</label>
          <input id="filtro-hora-inicio" v-model="filters.hora_inicio" type="time" />
        </div>
        <div class="form-row">
          <label for="filtro-hora-fin">Hora fin</label>
          <input id="filtro-hora-fin" v-model="filters.hora_fin" type="time" />
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
          <select id="filtro-institucion" v-model="filters.institucion_id" @change="onInstitucionChange">
            <option value="">Todas</option>
            <option v-for="item in sortedInstituciones" :key="item.id" :value="item.id">{{ institucionLabel(item) }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="filtro-complejo">Campus</label>
          <select id="filtro-complejo" v-model="filters.complejo_id" :disabled="!filters.institucion_id" @change="onComplejoChange">
            <option value="">Todos</option>
            <option v-for="item in filteredComplejos" :key="item.id" :value="item.id">{{ item.nombre }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="filtro-torre">Torre</label>
          <select id="filtro-torre" v-model="filters.torre_id" :disabled="!filters.complejo_id" @change="onTorreChange">
            <option value="">Todas</option>
            <option v-for="item in filteredTorres" :key="item.id" :value="item.id">{{ item.nombre }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="filtro-piso">Piso</label>
          <select id="filtro-piso" v-model="filters.piso_id" :disabled="!filters.torre_id" @change="onPisoChange">
            <option value="">Todos</option>
            <option v-for="item in filteredPisos" :key="item.id" :value="item.id">{{ pisoLabel(item) }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="filtro-consultorio">Consultorio</label>
          <select id="filtro-consultorio" v-model="filters.consultorio_id" :disabled="!filters.piso_id">
            <option value="">Todos</option>
            <option v-for="item in filteredConsultorios" :key="item.id" :value="item.id">{{ consultorioLabel(item) }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="filtro-medico">Médico</label>
          <select id="filtro-medico" v-model="filters.medico_id">
            <option value="">Todos</option>
            <option v-for="medico in medicos" :key="medico.id" :value="medico.id">
              {{ medicoLabel(medico) }}
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
          <p>{{ timeRangeLabel }} · {{ citas.length }} registros</p>
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
              <th>Estado</th>
              <th>Consultorio</th>
              <th>Estado cita</th>
              <th>Check-in</th>
              <th>Autorización</th>
              <th>Llamado</th>
              <th>Cancelación</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="cita in citas" :key="cita.id">
              <td>{{ cita.hora_cita.slice(0, 5) }}</td>
              <td><strong>{{ cita.folio_turno }}</strong></td>
              <td>{{ patientMedicalDisplay(cita) }}</td>
              <td>{{ cita.medico || cita.medico_id }}</td>
              <td>
                <button class="table-status-button" type="button" @click="showDoctorStatusDialog(cita)">
                  <span class="doctor-status-icon" :class="`doctor-status-${doctorStatusTone(cita.medico_estado_atencion)}`">
                    {{ doctorStatusIcon(cita.medico_estado_atencion) }}
                  </span>
                  {{ doctorStatusLabel(cita.medico_estado_atencion) }}
                </button>
              </td>
              <td>{{ cita.consultorio || cita.consultorio_id }}</td>
              <td><span class="status muted">{{ statusLabel(cita.estado) }}</span></td>
              <td>
                {{ shortDateTime(cita.fecha_hora_checkin) }}
                <br v-if="cita.tipo_checkin" />
                <small v-if="cita.tipo_checkin">{{ checkinTypeLabel(cita.tipo_checkin) }}</small>
              </td>
              <td>{{ shortDateTime(cita.fecha_hora_autorizar) }}</td>
              <td>{{ shortDateTime(cita.fecha_hora_llamar) }}</td>
              <td>
                {{ shortDateTime(cita.fecha_hora_cancelar) }}
                <br v-if="cita.tipo_cancelacion" />
                <small v-if="cita.tipo_cancelacion">{{ cancelTypeLabel(cita.tipo_cancelacion) }}</small>
              </td>
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
Torre {{ ticket.torre }}
{{ ticket.piso }}
Cita {{ ticket.hora }} hrs</pre>
      <p v-else class="message">QR listo para descargar o presentar en kiosko.</p>
    </div>

    <div v-if="selectedDoctorStatusCita" class="modal-backdrop">
      <div class="modal-panel" role="dialog" aria-modal="true" aria-labelledby="doctor-status-dialog-title">
        <h2 id="doctor-status-dialog-title">Estado del médico</h2>
        <dl class="dialog-details">
          <div>
            <dt>Médico</dt>
            <dd>{{ selectedDoctorStatusCita.medico || selectedDoctorStatusCita.medico_id }}</dd>
          </div>
          <div>
            <dt>Consultorio</dt>
            <dd>{{ selectedDoctorStatusCita.consultorio || selectedDoctorStatusCita.consultorio_id }}</dd>
          </div>
          <div>
            <dt>Estado</dt>
            <dd>
              <span class="doctor-status-value">
                <span class="doctor-status-icon" :class="`doctor-status-${doctorStatusTone(selectedDoctorStatusCita.medico_estado_atencion)}`">
                  {{ doctorStatusIcon(selectedDoctorStatusCita.medico_estado_atencion) }}
                </span>
                {{ doctorStatusLabel(selectedDoctorStatusCita.medico_estado_atencion) }}
              </span>
            </dd>
          </div>
          <div>
            <dt>Nota</dt>
            <dd>{{ selectedDoctorStatusCita.medico_notas_estado || 'Sin nota.' }}</dd>
          </div>
        </dl>
        <div class="actions-row">
          <button type="button" @click="selectedDoctorStatusCita = null">Ok</button>
        </div>
      </div>
    </div>
  </section>
</template>
