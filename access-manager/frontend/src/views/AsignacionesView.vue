<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import {
  activateResource,
  AsignacionMedicoConsultorio,
  AsignacionOperador,
  Complejo,
  Consultorio,
  createResource,
  deactivateResource,
  listAsignacionesMedicoConsultorio,
  listAsignacionesOperador,
  listComplejos,
  listConsultorios,
  listMedicos,
  listOperadores,
  Medico,
  Operador,
  updateResource,
} from '../api/client';
import { todayLocalIso } from '../dateUtils';

const asignacionesMedico = ref<AsignacionMedicoConsultorio[]>([]);
const asignacionesOperador = ref<AsignacionOperador[]>([]);
const medicos = ref<Medico[]>([]);
const consultorios = ref<Consultorio[]>([]);
const operadores = ref<Operador[]>([]);
const complejos = ref<Complejo[]>([]);
const error = ref('');
const loading = ref(false);
const editingMedicoId = ref<string | null>(null);
const editingOperadorId = ref<string | null>(null);

function today() {
  return todayLocalIso();
}

const medicoForm = reactive<Record<string, string | boolean>>({
  medico_id: '',
  consultorio_id: '',
  fecha_inicio: today(),
  fecha_fin: '',
  hora_inicio: '',
  hora_fin: '',
  dias_semana: '',
  activo: true,
});

const operadorForm = reactive<Record<string, string | number | boolean>>({
  operador_id: '',
  medico_id: '',
  consultorio_id: '',
  complejo_id: '',
  fecha_inicio: today(),
  fecha_fin: '',
  prioridad: 100,
  activo: true,
});

async function loadData() {
  loading.value = true;
  error.value = '';
  try {
    const [
      medicosData,
      consultoriosData,
      operadoresData,
      complejosData,
      medicoAssignmentsData,
      operadorAssignmentsData,
    ] = await Promise.all([
      listMedicos(),
      listConsultorios(),
      listOperadores(),
      listComplejos(),
      listAsignacionesMedicoConsultorio(),
      listAsignacionesOperador(),
    ]);
    medicos.value = medicosData;
    consultorios.value = consultoriosData;
    operadores.value = operadoresData;
    complejos.value = complejosData;
    asignacionesMedico.value = medicoAssignmentsData;
    asignacionesOperador.value = operadorAssignmentsData;
    medicoForm.medico_id ||= medicosData[0]?.id ?? '';
    medicoForm.consultorio_id ||= consultoriosData[0]?.id ?? '';
    operadorForm.operador_id ||= operadoresData[0]?.id ?? '';
    operadorForm.complejo_id ||= complejosData[0]?.id ?? '';
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar asignaciones.';
  } finally {
    loading.value = false;
  }
}

function nullable(value: unknown) {
  return value === '' ? null : value;
}

function medicoPayload() {
  return {
    medico_id: medicoForm.medico_id,
    consultorio_id: medicoForm.consultorio_id,
    fecha_inicio: medicoForm.fecha_inicio,
    fecha_fin: nullable(medicoForm.fecha_fin),
    hora_inicio: nullable(medicoForm.hora_inicio),
    hora_fin: nullable(medicoForm.hora_fin),
    dias_semana: nullable(medicoForm.dias_semana),
    activo: Boolean(medicoForm.activo),
  };
}

function operadorPayload() {
  return {
    operador_id: operadorForm.operador_id,
    medico_id: nullable(operadorForm.medico_id),
    consultorio_id: nullable(operadorForm.consultorio_id),
    complejo_id: operadorForm.complejo_id,
    fecha_inicio: operadorForm.fecha_inicio,
    fecha_fin: nullable(operadorForm.fecha_fin),
    prioridad: Number(operadorForm.prioridad),
    activo: Boolean(operadorForm.activo),
  };
}

async function saveMedicoAssignment() {
  loading.value = true;
  error.value = '';
  try {
    if (editingMedicoId.value) {
      await updateResource<AsignacionMedicoConsultorio>(
        'asignaciones-medico-consultorio',
        editingMedicoId.value,
        medicoPayload(),
      );
    } else {
      await createResource<AsignacionMedicoConsultorio>('asignaciones-medico-consultorio', medicoPayload());
    }
    resetMedicoForm();
    asignacionesMedico.value = await listAsignacionesMedicoConsultorio();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible guardar la asignación.';
  } finally {
    loading.value = false;
  }
}

async function saveOperadorAssignment() {
  loading.value = true;
  error.value = '';
  try {
    if (editingOperadorId.value) {
      await updateResource<AsignacionOperador>('asignaciones-operador', editingOperadorId.value, operadorPayload());
    } else {
      await createResource<AsignacionOperador>('asignaciones-operador', operadorPayload());
    }
    resetOperadorForm();
    asignacionesOperador.value = await listAsignacionesOperador();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible guardar la asignación.';
  } finally {
    loading.value = false;
  }
}

function resetMedicoForm() {
  editingMedicoId.value = null;
  medicoForm.medico_id = medicos.value[0]?.id ?? '';
  medicoForm.consultorio_id = consultorios.value[0]?.id ?? '';
  medicoForm.fecha_inicio = today();
  medicoForm.fecha_fin = '';
  medicoForm.hora_inicio = '';
  medicoForm.hora_fin = '';
  medicoForm.dias_semana = '';
  medicoForm.activo = true;
}

function resetOperadorForm() {
  editingOperadorId.value = null;
  operadorForm.operador_id = operadores.value[0]?.id ?? '';
  operadorForm.medico_id = '';
  operadorForm.consultorio_id = '';
  operadorForm.complejo_id = complejos.value[0]?.id ?? '';
  operadorForm.fecha_inicio = today();
  operadorForm.fecha_fin = '';
  operadorForm.prioridad = 100;
  operadorForm.activo = true;
}

function editMedicoAssignment(item: AsignacionMedicoConsultorio) {
  editingMedicoId.value = item.id;
  medicoForm.medico_id = item.medico_id;
  medicoForm.consultorio_id = item.consultorio_id;
  medicoForm.fecha_inicio = item.fecha_inicio;
  medicoForm.fecha_fin = item.fecha_fin ?? '';
  medicoForm.hora_inicio = item.hora_inicio ?? '';
  medicoForm.hora_fin = item.hora_fin ?? '';
  medicoForm.dias_semana = item.dias_semana ?? '';
  medicoForm.activo = item.activo;
}

function editOperadorAssignment(item: AsignacionOperador) {
  editingOperadorId.value = item.id;
  operadorForm.operador_id = item.operador_id;
  operadorForm.medico_id = item.medico_id ?? '';
  operadorForm.consultorio_id = item.consultorio_id ?? '';
  operadorForm.complejo_id = item.complejo_id;
  operadorForm.fecha_inicio = item.fecha_inicio;
  operadorForm.fecha_fin = item.fecha_fin ?? '';
  operadorForm.prioridad = item.prioridad;
  operadorForm.activo = item.activo;
}

async function setActive(resource: string, id: string, active: boolean) {
  loading.value = true;
  error.value = '';
  try {
    if (active) {
      await activateResource(resource, id);
    } else {
      await deactivateResource(resource, id);
    }
    asignacionesMedico.value = await listAsignacionesMedicoConsultorio();
    asignacionesOperador.value = await listAsignacionesOperador();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cambiar el estado.';
  } finally {
    loading.value = false;
  }
}

function medicoLabel(id: string | null | undefined) {
  const item = medicos.value.find((medico) => medico.id === id);
  return item ? item.nombre_visible || `${item.nombre} ${item.apellidos}` : 'Sin asignar';
}

function consultorioLabel(id: string | null | undefined) {
  const item = consultorios.value.find((consultorio) => consultorio.id === id);
  return item ? item.nombre_visible || item.codigo : 'Sin asignar';
}

function operadorLabel(id: string | null | undefined) {
  const item = operadores.value.find((operador) => operador.id === id);
  return item?.usuario_id ?? 'Sin asignar';
}

function complejoLabel(id: string | null | undefined) {
  return complejos.value.find((complejo) => complejo.id === id)?.nombre ?? 'Sin asignar';
}

onMounted(loadData);
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Asignaciones</h1>
        <p>Relación operativa entre médicos, consultorios y operadores.</p>
      </div>
    </header>

    <p v-if="error" class="error">{{ error }}</p>

    <div class="grid catalog-grid">
      <form class="panel form" @submit.prevent="saveMedicoAssignment">
        <h2>{{ editingMedicoId ? 'Editar' : 'Crear' }} asignación médico-consultorio</h2>
        <div class="form-row">
          <label for="medico">Médico</label>
          <select id="medico" v-model="medicoForm.medico_id" required>
            <option v-for="item in medicos" :key="item.id" :value="item.id">
              {{ item.nombre_visible || `${item.nombre} ${item.apellidos}` }}
            </option>
          </select>
        </div>
        <div class="form-row">
          <label for="consultorio">Consultorio</label>
          <select id="consultorio" v-model="medicoForm.consultorio_id" required>
            <option v-for="item in consultorios" :key="item.id" :value="item.id">
              {{ item.nombre_visible || item.codigo }}
            </option>
          </select>
        </div>
        <div class="form-grid">
          <div class="form-row">
            <label for="fecha-inicio-medico">Fecha inicio</label>
            <input id="fecha-inicio-medico" v-model="medicoForm.fecha_inicio" required type="date" />
          </div>
          <div class="form-row">
            <label for="fecha-fin-medico">Fecha fin</label>
            <input id="fecha-fin-medico" v-model="medicoForm.fecha_fin" type="date" />
          </div>
        </div>
        <div class="form-grid">
          <div class="form-row">
            <label for="hora-inicio-medico">Hora inicio</label>
            <input id="hora-inicio-medico" v-model="medicoForm.hora_inicio" type="time" />
          </div>
          <div class="form-row">
            <label for="hora-fin-medico">Hora fin</label>
            <input id="hora-fin-medico" v-model="medicoForm.hora_fin" type="time" />
          </div>
        </div>
        <div class="form-row">
          <label for="dias-semana">Días de semana</label>
          <input id="dias-semana" v-model="medicoForm.dias_semana" placeholder="Lun, Mar, Mié" />
        </div>
        <label class="check-row">
          <input v-model="medicoForm.activo" type="checkbox" />
          Activa
        </label>
        <div class="actions-row">
          <button type="submit" :disabled="loading">✓ Guardar</button>
          <button v-if="editingMedicoId" class="danger solid" type="button" @click="resetMedicoForm">× Cancelar</button>
        </div>
      </form>

      <form class="panel form" @submit.prevent="saveOperadorAssignment">
        <h2>{{ editingOperadorId ? 'Editar' : 'Crear' }} asignación de operador</h2>
        <div class="form-row">
          <label for="operador">Operador</label>
          <select id="operador" v-model="operadorForm.operador_id" required>
            <option v-for="item in operadores" :key="item.id" :value="item.id">{{ item.usuario_id }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="complejo">Complejo</label>
          <select id="complejo" v-model="operadorForm.complejo_id" required>
            <option v-for="item in complejos" :key="item.id" :value="item.id">{{ item.nombre }}</option>
          </select>
        </div>
        <div class="form-grid">
          <div class="form-row">
            <label for="operador-medico">Médico</label>
            <select id="operador-medico" v-model="operadorForm.medico_id">
              <option value="">Sin asignar</option>
              <option v-for="item in medicos" :key="item.id" :value="item.id">
                {{ item.nombre_visible || `${item.nombre} ${item.apellidos}` }}
              </option>
            </select>
          </div>
          <div class="form-row">
            <label for="operador-consultorio">Consultorio</label>
            <select id="operador-consultorio" v-model="operadorForm.consultorio_id">
              <option value="">Sin asignar</option>
              <option v-for="item in consultorios" :key="item.id" :value="item.id">
                {{ item.nombre_visible || item.codigo }}
              </option>
            </select>
          </div>
        </div>
        <div class="form-grid">
          <div class="form-row">
            <label for="fecha-inicio-operador">Fecha inicio</label>
            <input id="fecha-inicio-operador" v-model="operadorForm.fecha_inicio" required type="date" />
          </div>
          <div class="form-row">
            <label for="fecha-fin-operador">Fecha fin</label>
            <input id="fecha-fin-operador" v-model="operadorForm.fecha_fin" type="date" />
          </div>
        </div>
        <div class="form-row">
          <label for="prioridad">Prioridad</label>
          <input id="prioridad" v-model="operadorForm.prioridad" min="1" type="number" />
        </div>
        <label class="check-row">
          <input v-model="operadorForm.activo" type="checkbox" />
          Activa
        </label>
        <div class="actions-row">
          <button type="submit" :disabled="loading">✓ Guardar</button>
          <button v-if="editingOperadorId" class="danger solid" type="button" @click="resetOperadorForm">× Cancelar</button>
        </div>
      </form>
    </div>

    <section class="panel">
      <h2>Asignaciones médico-consultorio</h2>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Médico</th>
              <th>Consultorio</th>
              <th>Vigencia</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in asignacionesMedico" :key="item.id">
              <td>{{ medicoLabel(item.medico_id) }}</td>
              <td>{{ consultorioLabel(item.consultorio_id) }}</td>
              <td>{{ item.fecha_inicio }} - {{ item.fecha_fin || 'Sin fin' }}</td>
              <td><span class="status" :class="{ ok: item.activo, muted: !item.activo }">{{ item.activo ? 'Activa' : 'Inactiva' }}</span></td>
              <td>
                <div class="inline-actions">
                  <button class="small secondary" type="button" @click="editMedicoAssignment(item)">Editar</button>
                  <button v-if="item.activo" class="small danger" type="button" @click="setActive('asignaciones-medico-consultorio', item.id, false)">
                    Desactivar
                  </button>
                  <button v-else class="small secondary" type="button" @click="setActive('asignaciones-medico-consultorio', item.id, true)">
                    Activar
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <h2>Asignaciones de operador</h2>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Operador</th>
              <th>Complejo</th>
              <th>Médico</th>
              <th>Consultorio</th>
              <th>Prioridad</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in asignacionesOperador" :key="item.id">
              <td>{{ operadorLabel(item.operador_id) }}</td>
              <td>{{ complejoLabel(item.complejo_id) }}</td>
              <td>{{ medicoLabel(item.medico_id) }}</td>
              <td>{{ consultorioLabel(item.consultorio_id) }}</td>
              <td>{{ item.prioridad }}</td>
              <td><span class="status" :class="{ ok: item.activo, muted: !item.activo }">{{ item.activo ? 'Activa' : 'Inactiva' }}</span></td>
              <td>
                <div class="inline-actions">
                  <button class="small secondary" type="button" @click="editOperadorAssignment(item)">Editar</button>
                  <button v-if="item.activo" class="small danger" type="button" @click="setActive('asignaciones-operador', item.id, false)">
                    Desactivar
                  </button>
                  <button v-else class="small secondary" type="button" @click="setActive('asignaciones-operador', item.id, true)">
                    Activar
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>
