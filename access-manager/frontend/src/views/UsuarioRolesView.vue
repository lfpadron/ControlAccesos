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
import { todayLocalIso } from '../dateUtils';

const PAGE_SIZE = 20;

const assignments = ref<UsuarioRol[]>([]);
const usuarios = ref<Usuario[]>([]);
const allUsuarios = ref<Usuario[]>([]);
const roles = ref<Role[]>([]);
const instituciones = ref<Institucion[]>([]);
const campus = ref<Complejo[]>([]);
const torres = ref<Torre[]>([]);
const pisos = ref<Piso[]>([]);
const consultorios = ref<Consultorio[]>([]);
const medicos = ref<Medico[]>([]);
const selectedUserId = ref('');
const hasSearched = ref(false);
const usersLoaded = ref(false);
const loading = ref(false);
const loadingUsers = ref(false);
const error = ref('');
const message = ref('');
const page = ref(1);
const doctorSearch = ref('');

const filters = reactive({
  q: '',
  rol_id: '',
  estado: '',
});

const locationForm = reactive({
  institucionSearch: '',
  institucion_id: '',
  complejo_id: '',
  torre_id: '',
  piso_id: '',
  consultorio_id: '',
  fecha_inicio: todayLocalIso(),
  fecha_fin: '',
});

const doctorForm = reactive({
  medico_id: '',
  fecha_inicio: todayLocalIso(),
  fecha_fin: '',
});

const totalPages = computed(() => Math.max(1, Math.ceil(usuarios.value.length / PAGE_SIZE)));
const paginatedUsers = computed(() => usuarios.value.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE));
const selectedUser = computed(() => userById(selectedUserId.value));

const roleOptions = computed(() => sortByLabel(roles.value, roleLabelFromItem));
const sortedInstituciones = computed(() => sortByLabel(instituciones.value, institutionLabel));
const institutionOptions = computed(() => {
  const q = normalize(locationForm.institucionSearch);
  if (!q) return sortedInstituciones.value;
  return sortedInstituciones.value.filter((item) => normalize(institutionLabel(item)).includes(q));
});
const scopedCampus = computed(() =>
  locationForm.institucion_id
    ? sortByLabel(
        campus.value.filter((item) => item.institucion_id === locationForm.institucion_id),
        (item) => item.nombre,
      )
    : [],
);
const scopedTorres = computed(() =>
  locationForm.complejo_id
    ? sortByLabel(
        torres.value.filter((item) => item.complejo_id === locationForm.complejo_id),
        (item) => item.nombre,
      )
    : [],
);
const scopedPisos = computed(() =>
  locationForm.torre_id
    ? sortByLabel(
        pisos.value.filter((item) => item.torre_id === locationForm.torre_id),
        pisoLabel,
      )
    : [],
);
const scopedConsultorios = computed(() =>
  locationForm.piso_id
    ? sortByLabel(
        consultorios.value.filter((item) => item.piso_id === locationForm.piso_id),
        consultorioLabel,
      )
    : [],
);
const activeRoleForSelected = computed(() => {
  if (!selectedUserId.value) return null;
  const activeRows = assignments.value
    .filter((item) => item.usuario_id === selectedUserId.value && item.activo)
    .filter((item) => roles.value.some((role) => role.id === item.rol_id && role.activo))
    .sort((a, b) => roleLabel(a.rol_id).localeCompare(roleLabel(b.rol_id), 'es', { sensitivity: 'base' }));
  return activeRows[0] ?? null;
});
const selectedRoleLabel = computed(() => (activeRoleForSelected.value ? roleLabel(activeRoleForSelected.value.rol_id) : 'Sin rol activo'));
const locationAssignmentsForSelected = computed(() =>
  assignments.value
    .filter((item) => item.usuario_id === selectedUserId.value && !item.medico_id)
    .filter((item) => item.institucion_id || item.complejo_id || item.torre_id || item.piso_id || item.consultorio_id)
    .sort(compareAssignments),
);
const doctorAssignmentsForSelected = computed(() =>
  assignments.value
    .filter((item) => item.usuario_id === selectedUserId.value && Boolean(item.medico_id))
    .sort(compareAssignments),
);
const selectedDoctor = computed(() => medicos.value.find((item) => item.id === doctorForm.medico_id) ?? null);
const doctorOptions = computed(() => {
  const q = normalize(doctorSearch.value);
  const rows = sortByLabel(medicos.value, (item) => `${item.nombre} ${item.apellidos}`);
  if (!q) return rows;
  return rows.filter((item) => {
    const user = item.usuario_id ? userById(item.usuario_id) : null;
    const haystack = [item.nombre, item.apellidos, item.nombre_visible ?? '', user?.email ?? '', user?.correo_alterno ?? ''].join(' ');
    return normalize(haystack).includes(q);
  });
});

function normalize(value: string | null | undefined) {
  return (value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

function sortByLabel<T>(rows: T[], labeler: (item: T) => string) {
  return [...rows].sort((a, b) => labeler(a).localeCompare(labeler(b), 'es', { sensitivity: 'base' }));
}

function compareUsers(a: Usuario, b: Usuario) {
  return `${a.apellidos} ${a.nombre}`.localeCompare(`${b.apellidos} ${b.nombre}`, 'es', { sensitivity: 'base' });
}

function compareAssignments(a: UsuarioRol, b: UsuarioRol) {
  const startCompare = (a.fecha_inicio ?? '').localeCompare(b.fecha_inicio ?? '');
  if (startCompare !== 0) return startCompare;
  return assignmentScope(a).localeCompare(assignmentScope(b), 'es', { sensitivity: 'base' });
}

function userById(id: string) {
  return allUsuarios.value.find((item) => item.id === id) ?? usuarios.value.find((item) => item.id === id) ?? null;
}

function userLabel(user: Usuario) {
  return `${user.apellidos}, ${user.nombre} (${user.email})`;
}

function roleLabelFromItem(role: Role) {
  return role.nombre || role.codigo;
}

function roleLabel(id: string) {
  const role = roles.value.find((item) => item.id === id);
  return role ? roleLabelFromItem(role) : '-';
}

function roleText(userId: string) {
  const labels = [
    ...new Set(
      assignments.value
        .filter((item) => item.usuario_id === userId && item.activo)
        .map((item) => roleLabel(item.rol_id)),
    ),
  ];
  return labels.length ? labels.join(', ') : 'Sin rol asignado';
}

function institutionLabel(item: Institucion) {
  return item.nombre;
}

function pisoLabel(item: Piso) {
  const detail = item.codigo || item.nombre_visible;
  return detail ? `Piso ${item.numero} - ${detail}` : `Piso ${item.numero}`;
}

function consultorioLabel(item: Consultorio) {
  const description = item.nombre_visible || item.instrucciones_acceso || 'Sin descripción';
  return `${item.codigo} - ${description}`;
}

function medicoLabel(item: Medico) {
  const user = item.usuario_id ? userById(item.usuario_id) : null;
  const email = user?.email ? ` (${user.email})` : '';
  return `${item.nombre} ${item.apellidos}${email}`;
}

function medicoDisplay(item: Medico) {
  const user = item.usuario_id ? userById(item.usuario_id) : null;
  return {
    apellidos: item.apellidos,
    nombre: item.nombre,
    correo: user?.email ?? '-',
  };
}

function optionName<T extends { id: string }>(rows: T[], id: string | null | undefined, labeler: (item: T) => string) {
  if (!id) return '-';
  const row = rows.find((item) => item.id === id);
  return row ? labeler(row) : '-';
}

function assignmentScope(item: UsuarioRol) {
  if (item.consultorio_id) return `Consultorio: ${optionName(consultorios.value, item.consultorio_id, consultorioLabel)}`;
  if (item.piso_id) return `Piso: ${optionName(pisos.value, item.piso_id, pisoLabel)}`;
  if (item.torre_id) return `Torre: ${optionName(torres.value, item.torre_id, (row) => row.nombre)}`;
  if (item.complejo_id) return `Campus: ${optionName(campus.value, item.complejo_id, (row) => row.nombre)}`;
  if (item.institucion_id) return `Institución: ${optionName(instituciones.value, item.institucion_id, institutionLabel)}`;
  return '-';
}

function doctorAssignmentLabel(item: UsuarioRol) {
  return optionName(medicos.value, item.medico_id, medicoLabel);
}

function dateText(value: string | null | undefined) {
  return value || '-';
}

function resetLocationForm() {
  locationForm.institucionSearch = '';
  locationForm.institucion_id = '';
  locationForm.complejo_id = '';
  locationForm.torre_id = '';
  locationForm.piso_id = '';
  locationForm.consultorio_id = '';
  locationForm.fecha_inicio = todayLocalIso();
  locationForm.fecha_fin = '';
}

function resetDoctorForm() {
  doctorSearch.value = '';
  doctorForm.medico_id = '';
  doctorForm.fecha_inicio = todayLocalIso();
  doctorForm.fecha_fin = '';
}

function resetLowerLocation(level: 'institucion' | 'campus' | 'torre' | 'piso') {
  if (level === 'institucion') locationForm.complejo_id = '';
  if (level === 'institucion' || level === 'campus') locationForm.torre_id = '';
  if (level === 'institucion' || level === 'campus' || level === 'torre') locationForm.piso_id = '';
  locationForm.consultorio_id = '';
}

function syncInstitutionFromSearch() {
  const value = normalize(locationForm.institucionSearch);
  const match = sortedInstituciones.value.find((item) => normalize(institutionLabel(item)) === value);
  const nextId = match?.id ?? '';
  if (locationForm.institucion_id !== nextId) {
    locationForm.institucion_id = nextId;
    resetLowerLocation('institucion');
  }
}

function syncCampus() {
  if (!scopedCampus.value.some((item) => item.id === locationForm.complejo_id)) {
    locationForm.complejo_id = '';
  }
  resetLowerLocation('campus');
}

function syncTorre() {
  if (!scopedTorres.value.some((item) => item.id === locationForm.torre_id)) {
    locationForm.torre_id = '';
  }
  resetLowerLocation('torre');
}

function syncPiso() {
  if (!scopedPisos.value.some((item) => item.id === locationForm.piso_id)) {
    locationForm.piso_id = '';
  }
  resetLowerLocation('piso');
}

function selectedRoleId() {
  const roleId = activeRoleForSelected.value?.rol_id;
  if (!selectedUserId.value) {
    error.value = 'Seleccione un usuario de la tabla o del dropdown.';
    return '';
  }
  if (!roleId) {
    error.value = 'El usuario seleccionado no tiene un rol activo. Asigne un rol en la pantalla Usuarios.';
    return '';
  }
  return roleId;
}

function validateDates(fechaInicio: string, fechaFin: string) {
  if (!fechaInicio) {
    error.value = 'Indique fecha de inicio de vigencia.';
    return false;
  }
  if (fechaFin && fechaFin < fechaInicio) {
    error.value = 'La fecha de fin no puede ser menor que la fecha de inicio.';
    return false;
  }
  return true;
}

async function loadReferenceData() {
  loading.value = true;
  error.value = '';
  try {
    const [assignmentsData, rolesData, institucionesData, campusData, torresData, pisosData, consultoriosData, medicosData] = await Promise.all([
      listUsuarioRoles(),
      listRoles(),
      listInstituciones(),
      listComplejos(),
      listTorres(),
      listPisos(),
      listConsultorios(),
      listMedicos(),
    ]);
    assignments.value = assignmentsData;
    roles.value = rolesData;
    instituciones.value = institucionesData;
    campus.value = campusData;
    torres.value = torresData;
    pisos.value = pisosData;
    consultorios.value = consultoriosData;
    medicos.value = medicosData;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar catálogos de asignación.';
  } finally {
    loading.value = false;
  }
}

async function ensureUsersLoaded() {
  if (usersLoaded.value || loadingUsers.value) return;
  loadingUsers.value = true;
  try {
    allUsuarios.value = await listUsuarios();
    usersLoaded.value = true;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar usuarios.';
  } finally {
    loadingUsers.value = false;
  }
}

async function reloadAssignments() {
  assignments.value = await listUsuarioRoles();
}

async function searchUsers() {
  loading.value = true;
  error.value = '';
  message.value = '';
  try {
    const usersData = await listUsuarios();
    allUsuarios.value = usersData;
    usersLoaded.value = true;
    const q = normalize(filters.q);
    const result = usersData
      .filter((user) => {
        if (q) {
          const haystack = [user.apellidos, user.nombre, user.email, user.correo_alterno ?? ''].join(' ');
          if (!normalize(haystack).includes(q)) return false;
        }
        if (filters.rol_id && !assignments.value.some((item) => item.usuario_id === user.id && item.rol_id === filters.rol_id && item.activo)) {
          return false;
        }
        const isActive = user.estado === 'ACTIVO';
        if (filters.estado === 'activo' && !isActive) return false;
        if (filters.estado === 'inactivo' && isActive) return false;
        return true;
      })
      .sort(compareUsers);
    usuarios.value = result;
    hasSearched.value = true;
    page.value = 1;
    if (selectedUserId.value && !result.some((item) => item.id === selectedUserId.value)) {
      selectedUserId.value = '';
      resetLocationForm();
      resetDoctorForm();
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible buscar usuarios.';
  } finally {
    loading.value = false;
  }
}

function clearUserSearch() {
  filters.q = '';
  filters.rol_id = '';
  filters.estado = '';
  usuarios.value = [];
  selectedUserId.value = '';
  hasSearched.value = false;
  page.value = 1;
  resetLocationForm();
  resetDoctorForm();
}

function selectUser(user: Usuario) {
  selectedUserId.value = user.id;
  message.value = '';
}

async function addLocationAssignment() {
  error.value = '';
  message.value = '';
  const roleId = selectedRoleId();
  if (!roleId) return;
  if (!locationForm.institucion_id) {
    error.value = 'Seleccione una institución para crear la asignación.';
    return;
  }
  if (!validateDates(locationForm.fecha_inicio, locationForm.fecha_fin)) return;
  loading.value = true;
  try {
    await createUsuarioRol({
      usuario_id: selectedUserId.value,
      rol_id: roleId,
      institucion_id: locationForm.institucion_id,
      complejo_id: locationForm.complejo_id || null,
      torre_id: locationForm.torre_id || null,
      piso_id: locationForm.piso_id || null,
      consultorio_id: locationForm.consultorio_id || null,
      medico_id: null,
      fecha_inicio: locationForm.fecha_inicio,
      fecha_fin: locationForm.fecha_fin || null,
      activo: true,
    });
    await reloadAssignments();
    message.value = 'Asignación a consultorios creada.';
    resetLocationForm();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible crear la asignación a consultorios.';
  } finally {
    loading.value = false;
  }
}

async function addDoctorAssignment() {
  error.value = '';
  message.value = '';
  const roleId = selectedRoleId();
  if (!roleId) return;
  if (!doctorForm.medico_id) {
    error.value = 'Seleccione un médico.';
    return;
  }
  if (!validateDates(doctorForm.fecha_inicio, doctorForm.fecha_fin)) return;
  loading.value = true;
  try {
    await createUsuarioRol({
      usuario_id: selectedUserId.value,
      rol_id: roleId,
      institucion_id: null,
      complejo_id: null,
      torre_id: null,
      piso_id: null,
      consultorio_id: null,
      medico_id: doctorForm.medico_id,
      fecha_inicio: doctorForm.fecha_inicio,
      fecha_fin: doctorForm.fecha_fin || null,
      activo: true,
    });
    await reloadAssignments();
    message.value = 'Asignación a médicos creada.';
    resetDoctorForm();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible crear la asignación a médicos.';
  } finally {
    loading.value = false;
  }
}

async function deactivateAssignment(item: UsuarioRol) {
  error.value = '';
  message.value = '';
  loading.value = true;
  try {
    await updateUsuarioRol(item.id, { activo: false });
    await reloadAssignments();
    message.value = 'Asignación desactivada.';
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible desactivar la asignación.';
  } finally {
    loading.value = false;
  }
}

function onDoctorSearchInput() {
  void ensureUsersLoaded();
  const value = normalize(doctorSearch.value);
  const match = doctorOptions.value.find((item) => normalize(medicoLabel(item)) === value || normalize(`${item.nombre} ${item.apellidos}`) === value);
  doctorForm.medico_id = match?.id ?? '';
}

onMounted(loadReferenceData);
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Asignación de usuarios</h1>
        <p>Alcances operativos por consultorios y médicos.</p>
      </div>
    </header>

    <section class="panel">
      <div class="form-grid">
        <div class="form-row">
          <label for="asignacion-q">Nombre o correo</label>
          <input id="asignacion-q" v-model="filters.q" @keyup.enter="searchUsers" />
        </div>
        <div class="form-row">
          <label for="asignacion-role-filter">Rol</label>
          <select id="asignacion-role-filter" v-model="filters.rol_id">
            <option value="">Todos los roles</option>
            <option v-for="role in roleOptions" :key="role.id" :value="role.id">{{ roleLabelFromItem(role) }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="asignacion-active-filter">Estado</label>
          <select id="asignacion-active-filter" v-model="filters.estado">
            <option value="">Todos</option>
            <option value="activo">Activo</option>
            <option value="inactivo">Inactivo</option>
          </select>
        </div>
      </div>
      <div class="actions-row">
        <button type="button" :disabled="loading" @click="searchUsers">{{ loading ? 'Buscando...' : 'Buscar' }}</button>
        <button class="secondary" type="button" @click="clearUserSearch">Limpiar</button>
      </div>
    </section>

    <section class="panel table-panel">
      <div class="form-row">
        <label for="asignacion-user-select">Usuario seleccionado</label>
        <select id="asignacion-user-select" v-model="selectedUserId" :disabled="usuarios.length === 0">
          <option value="">Seleccione usuario desde resultados</option>
          <option v-for="user in usuarios" :key="user.id" :value="user.id">{{ userLabel(user) }}</option>
        </select>
      </div>
      <p v-if="selectedUser" class="message">Rol activo usado para nuevas asignaciones: {{ selectedRoleLabel }}</p>

      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Apellido(s)</th>
              <th>Nombre</th>
              <th>Correo</th>
              <th>Correo alterno</th>
              <th>Rol</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in paginatedUsers" :key="user.id" class="selectable-row" :class="{ selected: selectedUserId === user.id }" @click="selectUser(user)">
              <td>{{ user.apellidos }}</td>
              <td>{{ user.nombre }}</td>
              <td>{{ user.email }}</td>
              <td>{{ user.correo_alterno || '-' }}</td>
              <td>{{ roleText(user.id) }}</td>
              <td>{{ user.estado }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="!loading && !hasSearched" class="message">Use Buscar para consultar usuarios.</p>
      <p v-else-if="!loading && usuarios.length === 0" class="message">No hay usuarios para mostrar.</p>
      <div class="actions-row">
        <button class="secondary" type="button" :disabled="page <= 1" @click="page -= 1">Anterior</button>
        <span class="message">Página {{ page }} de {{ totalPages }}</span>
        <button class="secondary" type="button" :disabled="page >= totalPages" @click="page += 1">Siguiente</button>
      </div>
    </section>

    <p v-if="message" class="message">{{ message }}</p>
    <p v-if="error" class="error">{{ error }}</p>

    <div class="grid catalog-grid">
      <section class="panel form">
        <h2>Asignación a consultorios</h2>
        <p v-if="!selectedUser" class="message">Seleccione un usuario para habilitar asignaciones.</p>
        <div class="form-row">
          <label for="asignacion-institucion-search">Institución</label>
          <input
            id="asignacion-institucion-search"
            v-model="locationForm.institucionSearch"
            :disabled="!selectedUser"
            list="instituciones-asignacion"
            @input="syncInstitutionFromSearch"
          />
          <datalist id="instituciones-asignacion">
            <option v-for="item in institutionOptions" :key="item.id" :value="institutionLabel(item)" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="asignacion-campus">Campus</label>
          <select id="asignacion-campus" v-model="locationForm.complejo_id" :disabled="!selectedUser || !locationForm.institucion_id" @change="syncCampus">
            <option value="">Toda la institución</option>
            <option v-for="item in scopedCampus" :key="item.id" :value="item.id">{{ item.nombre }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="asignacion-torre">Torre</label>
          <select id="asignacion-torre" v-model="locationForm.torre_id" :disabled="!selectedUser || !locationForm.complejo_id" @change="syncTorre">
            <option value="">Todo el campus</option>
            <option v-for="item in scopedTorres" :key="item.id" :value="item.id">{{ item.nombre }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="asignacion-piso">Piso</label>
          <select id="asignacion-piso" v-model="locationForm.piso_id" :disabled="!selectedUser || !locationForm.torre_id" @change="syncPiso">
            <option value="">Toda la torre</option>
            <option v-for="item in scopedPisos" :key="item.id" :value="item.id">{{ pisoLabel(item) }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="asignacion-consultorio">Consultorio</label>
          <select id="asignacion-consultorio" v-model="locationForm.consultorio_id" :disabled="!selectedUser || !locationForm.piso_id">
            <option value="">Todo el piso</option>
            <option v-for="item in scopedConsultorios" :key="item.id" :value="item.id">{{ consultorioLabel(item) }}</option>
          </select>
        </div>
        <div class="form-grid">
          <div class="form-row">
            <label for="ubicacion-fecha-inicio">Inicio de vigencia</label>
            <input id="ubicacion-fecha-inicio" v-model="locationForm.fecha_inicio" :disabled="!selectedUser" required type="date" />
          </div>
          <div class="form-row">
            <label for="ubicacion-fecha-fin">Fin de vigencia</label>
            <input id="ubicacion-fecha-fin" v-model="locationForm.fecha_fin" :disabled="!selectedUser" type="date" />
          </div>
        </div>
        <div class="actions-row">
          <button type="button" :disabled="loading || !selectedUser" @click="addLocationAssignment">Agregar asignación</button>
          <button class="secondary" type="button" @click="resetLocationForm">Limpiar</button>
        </div>

        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Alcance</th>
                <th>Inicio</th>
                <th>Fin</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in locationAssignmentsForSelected" :key="item.id">
                <td>{{ assignmentScope(item) }}</td>
                <td>{{ dateText(item.fecha_inicio) }}</td>
                <td>{{ dateText(item.fecha_fin) }}</td>
                <td>{{ item.activo ? 'Activo' : 'Inactivo' }}</td>
                <td>
                  <button v-if="item.activo" class="small danger" type="button" :disabled="loading" @click="deactivateAssignment(item)">Desactivar</button>
                  <span v-else>-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="selectedUser && locationAssignmentsForSelected.length === 0" class="message">Sin asignaciones a consultorios.</p>
      </section>

      <section class="panel form">
        <h2>Asignación a médicos</h2>
        <p v-if="!selectedUser" class="message">Seleccione un usuario para habilitar asignaciones.</p>
        <div class="form-row">
          <label for="asignacion-medico-search">Médico</label>
          <input
            id="asignacion-medico-search"
            v-model="doctorSearch"
            :disabled="!selectedUser"
            list="medicos-asignacion"
            @focus="ensureUsersLoaded"
            @input="onDoctorSearchInput"
          />
          <datalist id="medicos-asignacion">
            <option v-for="item in doctorOptions" :key="item.id" :value="medicoLabel(item)" />
          </datalist>
        </div>
        <div v-if="selectedDoctor" class="form-grid">
          <div class="form-row">
            <label>Apellido(s)</label>
            <input :value="medicoDisplay(selectedDoctor).apellidos" disabled />
          </div>
          <div class="form-row">
            <label>Nombre</label>
            <input :value="medicoDisplay(selectedDoctor).nombre" disabled />
          </div>
          <div class="form-row">
            <label>Correo</label>
            <input :value="medicoDisplay(selectedDoctor).correo" disabled />
          </div>
        </div>
        <div class="form-grid">
          <div class="form-row">
            <label for="medico-fecha-inicio">Inicio de vigencia</label>
            <input id="medico-fecha-inicio" v-model="doctorForm.fecha_inicio" :disabled="!selectedUser" required type="date" />
          </div>
          <div class="form-row">
            <label for="medico-fecha-fin">Fin de vigencia</label>
            <input id="medico-fecha-fin" v-model="doctorForm.fecha_fin" :disabled="!selectedUser" type="date" />
          </div>
        </div>
        <div class="actions-row">
          <button type="button" :disabled="loading || !selectedUser" @click="addDoctorAssignment">Agregar asignación</button>
          <button class="secondary" type="button" @click="resetDoctorForm">Limpiar</button>
        </div>

        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Médico</th>
                <th>Inicio</th>
                <th>Fin</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in doctorAssignmentsForSelected" :key="item.id">
                <td>{{ doctorAssignmentLabel(item) }}</td>
                <td>{{ dateText(item.fecha_inicio) }}</td>
                <td>{{ dateText(item.fecha_fin) }}</td>
                <td>{{ item.activo ? 'Activo' : 'Inactivo' }}</td>
                <td>
                  <button v-if="item.activo" class="small danger" type="button" :disabled="loading" @click="deactivateAssignment(item)">Desactivar</button>
                  <span v-else>-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="selectedUser && doctorAssignmentsForSelected.length === 0" class="message">Sin asignaciones a médicos.</p>
      </section>
    </div>
  </section>
</template>
