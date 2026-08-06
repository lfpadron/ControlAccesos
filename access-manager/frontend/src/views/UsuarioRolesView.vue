<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import {
  createUsuarioRol,
  listComplejos,
  listConsultorios,
  listInstituciones,
  listMedicos,
  listPisos,
  listRoles,
  listTorres,
  listUsuarioRoles,
  listUsuarios,
  updateUsuarioRol,
  type Complejo,
  type Consultorio,
  type Institucion,
  type Medico,
  type Piso,
  type Role,
  type Torre,
  type Usuario,
  type UsuarioRol,
} from '../api/client';

const PAGE_SIZE = 20;

const assignments = ref<UsuarioRol[]>([]);
const usuarios = ref<Usuario[]>([]);
const roles = ref<Role[]>([]);
const instituciones = ref<Institucion[]>([]);
const campus = ref<Complejo[]>([]);
const torres = ref<Torre[]>([]);
const pisos = ref<Piso[]>([]);
const consultorios = ref<Consultorio[]>([]);
const medicos = ref<Medico[]>([]);
const selected = ref<UsuarioRol | null>(null);
const loading = ref(false);
const error = ref('');
const message = ref('');
const page = ref(1);

const filters = reactive({ q: '', rol_id: '', activo: '' });
const appliedFilters = reactive({ q: '', rol_id: '', activo: '' });

const form = reactive({
  usuario_id: '',
  rol_id: '',
  institucion_id: '',
  complejo_id: '',
  torre_id: '',
  piso_id: '',
  consultorio_id: '',
  medico_id: '',
  activo: true,
});

const scopedCampus = computed(() => (form.institucion_id ? campus.value.filter((item) => item.institucion_id === form.institucion_id) : campus.value));
const scopedTorres = computed(() => (form.complejo_id ? torres.value.filter((item) => item.complejo_id === form.complejo_id) : []));
const scopedPisos = computed(() => (form.torre_id ? pisos.value.filter((item) => item.torre_id === form.torre_id) : []));
const scopedConsultorios = computed(() => (form.piso_id ? consultorios.value.filter((item) => item.piso_id === form.piso_id) : []));

const filteredAssignments = computed(() => {
  const q = appliedFilters.q.trim().toLowerCase();
  return assignments.value.filter((assignment) => {
    const user = userById(assignment.usuario_id);
    if (q) {
      const haystack = [user?.nombre ?? '', user?.email ?? '', user?.correo_alterno ?? ''].join(' ').toLowerCase();
      if (!haystack.includes(q)) return false;
    }
    if (appliedFilters.rol_id && assignment.rol_id !== appliedFilters.rol_id) return false;
    if (appliedFilters.activo === 'activo' && !assignment.activo) return false;
    if (appliedFilters.activo === 'inactivo' && assignment.activo) return false;
    return true;
  });
});

const totalPages = computed(() => Math.max(1, Math.ceil(filteredAssignments.value.length / PAGE_SIZE)));
const paginatedAssignments = computed(() => filteredAssignments.value.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE));

function userById(id: string) {
  return usuarios.value.find((item) => item.id === id) ?? null;
}

function roleLabel(id: string) {
  const role = roles.value.find((item) => item.id === id);
  return role ? role.nombre || role.codigo : '-';
}

function optionName<T extends { id: string }>(rows: T[], id: string | null | undefined, labeler: (item: T) => string) {
  if (!id) return '-';
  const row = rows.find((item) => item.id === id);
  return row ? labeler(row) : '-';
}

function userLabel(id: string) {
  const user = userById(id);
  return user ? `${user.nombre} (${user.email})` : '-';
}

function medicoLabel(item: Medico) {
  return item.nombre_visible || `${item.nombre} ${item.apellidos}`;
}

function resetForm() {
  selected.value = null;
  form.usuario_id = '';
  form.rol_id = '';
  form.institucion_id = '';
  form.complejo_id = '';
  form.torre_id = '';
  form.piso_id = '';
  form.consultorio_id = '';
  form.medico_id = '';
  form.activo = true;
}

function editAssignment(item: UsuarioRol) {
  selected.value = item;
  form.usuario_id = item.usuario_id;
  form.rol_id = item.rol_id;
  form.institucion_id = item.institucion_id ?? '';
  form.complejo_id = item.complejo_id ?? '';
  form.torre_id = item.torre_id ?? '';
  form.piso_id = item.piso_id ?? '';
  form.consultorio_id = item.consultorio_id ?? '';
  form.medico_id = item.medico_id ?? '';
  form.activo = item.activo;
}

function syncInstitution() {
  if (!scopedCampus.value.some((item) => item.id === form.complejo_id)) {
    form.complejo_id = '';
  }
  syncCampus();
}

function syncCampus() {
  const selectedCampus = campus.value.find((item) => item.id === form.complejo_id);
  if (selectedCampus && form.institucion_id !== selectedCampus.institucion_id) {
    form.institucion_id = selectedCampus.institucion_id;
  }
  if (!scopedTorres.value.some((item) => item.id === form.torre_id)) {
    form.torre_id = '';
  }
  syncTorre();
}

function syncTorre() {
  if (!scopedPisos.value.some((item) => item.id === form.piso_id)) {
    form.piso_id = '';
  }
  syncPiso();
}

function syncPiso() {
  if (!scopedConsultorios.value.some((item) => item.id === form.consultorio_id)) {
    form.consultorio_id = '';
  }
}

function applyFilters() {
  appliedFilters.q = filters.q;
  appliedFilters.rol_id = filters.rol_id;
  appliedFilters.activo = filters.activo;
  page.value = 1;
}

function clearFilters() {
  filters.q = '';
  filters.rol_id = '';
  filters.activo = '';
  applyFilters();
}

async function loadData() {
  loading.value = true;
  error.value = '';
  try {
    const [assignmentsData, usersData, rolesData, institucionesData, campusData, torresData, pisosData, consultoriosData, medicosData] = await Promise.all([
      listUsuarioRoles(),
      listUsuarios(),
      listRoles(),
      listInstituciones(),
      listComplejos(),
      listTorres(),
      listPisos(),
      listConsultorios(),
      listMedicos(),
    ]);
    assignments.value = assignmentsData;
    usuarios.value = usersData;
    roles.value = rolesData;
    instituciones.value = institucionesData;
    campus.value = campusData;
    torres.value = torresData;
    pisos.value = pisosData;
    consultorios.value = consultoriosData;
    medicos.value = medicosData;
    if (page.value > totalPages.value) page.value = totalPages.value;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar asignaciones.';
  } finally {
    loading.value = false;
  }
}

async function submit() {
  error.value = '';
  message.value = '';
  loading.value = true;
  try {
    const payload = {
      usuario_id: form.usuario_id,
      rol_id: form.rol_id,
      institucion_id: form.institucion_id || null,
      complejo_id: form.complejo_id || null,
      torre_id: form.torre_id || null,
      piso_id: form.piso_id || null,
      consultorio_id: form.consultorio_id || null,
      medico_id: form.medico_id || null,
      activo: form.activo,
    };
    if (selected.value) {
      await updateUsuarioRol(selected.value.id, payload);
      message.value = 'Asignación actualizada.';
    } else {
      await createUsuarioRol(payload);
      message.value = 'Asignación creada.';
    }
    await loadData();
    resetForm();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible guardar la asignación.';
  } finally {
    loading.value = false;
  }
}

onMounted(loadData);
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Asignación de usuarios</h1>
        <p>Roles y alcances operativos por ubicación o médico.</p>
      </div>
    </header>

    <section class="panel">
      <div class="form-grid">
        <div class="form-row">
          <label for="asignacion-q">Nombre o correo</label>
          <input id="asignacion-q" v-model="filters.q" @keyup.enter="applyFilters" />
        </div>
        <div class="form-row">
          <label for="asignacion-role-filter">Rol</label>
          <select id="asignacion-role-filter" v-model="filters.rol_id">
            <option value="">Todos los roles</option>
            <option v-for="role in roles" :key="role.id" :value="role.id">{{ role.nombre || role.codigo }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="asignacion-active-filter">Estado</label>
          <select id="asignacion-active-filter" v-model="filters.activo">
            <option value="">Todos</option>
            <option value="activo">Activo</option>
            <option value="inactivo">Inactivo</option>
          </select>
        </div>
      </div>
      <div class="actions-row">
        <button type="button" @click="applyFilters">Buscar</button>
        <button class="secondary" type="button" @click="clearFilters">Limpiar</button>
      </div>
    </section>

    <div class="grid catalog-grid">
      <form class="panel form" @submit.prevent="submit">
        <h2>{{ selected ? 'Editar asignación' : 'Crear asignación' }}</h2>
        <div class="form-row">
          <label for="asignacion-user">Usuario</label>
          <select id="asignacion-user" v-model="form.usuario_id" required>
            <option value="">Seleccione usuario</option>
            <option v-for="user in usuarios" :key="user.id" :value="user.id">{{ user.nombre }} ({{ user.email }})</option>
          </select>
        </div>
        <div class="form-row">
          <label for="asignacion-role">Rol</label>
          <select id="asignacion-role" v-model="form.rol_id" required>
            <option value="">Seleccione rol</option>
            <option v-for="role in roles" :key="role.id" :value="role.id">{{ role.nombre || role.codigo }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="asignacion-institucion">Institución</label>
          <select id="asignacion-institucion" v-model="form.institucion_id" @change="syncInstitution">
            <option value="">Sin asignar</option>
            <option v-for="item in instituciones" :key="item.id" :value="item.id">{{ item.nombre }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="asignacion-campus">Campus</label>
          <select id="asignacion-campus" v-model="form.complejo_id" @change="syncCampus">
            <option value="">Sin asignar</option>
            <option v-for="item in scopedCampus" :key="item.id" :value="item.id">{{ item.nombre }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="asignacion-torre">Torre</label>
          <select id="asignacion-torre" v-model="form.torre_id" :disabled="!form.complejo_id" @change="syncTorre">
            <option value="">Sin asignar</option>
            <option v-for="item in scopedTorres" :key="item.id" :value="item.id">{{ item.nombre }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="asignacion-piso">Piso</label>
          <select id="asignacion-piso" v-model="form.piso_id" :disabled="!form.torre_id" @change="syncPiso">
            <option value="">Sin asignar</option>
            <option v-for="item in scopedPisos" :key="item.id" :value="item.id">{{ item.nombre_visible }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="asignacion-consultorio">Consultorio</label>
          <select id="asignacion-consultorio" v-model="form.consultorio_id" :disabled="!form.piso_id">
            <option value="">Sin asignar</option>
            <option v-for="item in scopedConsultorios" :key="item.id" :value="item.id">{{ item.nombre_visible || item.codigo }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="asignacion-medico">Médico</label>
          <select id="asignacion-medico" v-model="form.medico_id">
            <option value="">Sin asignar</option>
            <option v-for="item in medicos" :key="item.id" :value="item.id">{{ medicoLabel(item) }}</option>
          </select>
        </div>
        <label class="check-row">
          <input v-model="form.activo" type="checkbox" />
          Activo
        </label>
        <p v-if="message" class="message">{{ message }}</p>
        <p v-if="error" class="error">{{ error }}</p>
        <div class="actions-row">
          <button type="submit" :disabled="loading">{{ loading ? 'Guardando...' : '✓ Guardar' }}</button>
          <button class="danger solid" type="button" @click="resetForm">× Cancelar</button>
        </div>
      </form>

      <section class="panel table-panel">
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Usuario</th>
                <th>Rol</th>
                <th>Campus</th>
                <th>Torre</th>
                <th>Piso</th>
                <th>Consultorio</th>
                <th>Médico</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in paginatedAssignments" :key="item.id" class="selectable-row" :class="{ selected: selected?.id === item.id }" @click="editAssignment(item)">
                <td>{{ userLabel(item.usuario_id) }}</td>
                <td>{{ roleLabel(item.rol_id) }}</td>
                <td>{{ optionName(campus, item.complejo_id, (row) => row.nombre) }}</td>
                <td>{{ optionName(torres, item.torre_id, (row) => row.nombre) }}</td>
                <td>{{ optionName(pisos, item.piso_id, (row) => row.nombre_visible) }}</td>
                <td>{{ optionName(consultorios, item.consultorio_id, (row) => row.nombre_visible || row.codigo) }}</td>
                <td>{{ optionName(medicos, item.medico_id, medicoLabel) }}</td>
                <td>{{ item.activo ? 'Activo' : 'Inactivo' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="!loading && filteredAssignments.length === 0" class="message">No hay asignaciones para mostrar.</p>
        <div class="actions-row">
          <button class="secondary" type="button" :disabled="page <= 1" @click="page -= 1">Anterior</button>
          <span class="message">Página {{ page }} de {{ totalPages }}</span>
          <button class="secondary" type="button" :disabled="page >= totalPages" @click="page += 1">Siguiente</button>
        </div>
      </section>
    </div>
  </section>
</template>
