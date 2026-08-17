<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import {
  listAsignacionesMedicoConsultorio,
  listAsignacionesOperador,
  listComplejos,
  listConsultorios,
  listInstituciones,
  listMedicos,
  listOperadores,
  listPisos,
  listRoles,
  listTorres,
  listUsuarioRoles,
  listUsuarios,
  type AsignacionMedicoConsultorio,
  type AsignacionOperador,
  type Complejo,
  type Consultorio,
  type Institucion,
  type Medico,
  type Operador,
  type Piso,
  type Role,
  type Torre,
  type Usuario,
  type UsuarioRol,
} from '../api/client';
import { exportRows, type ExportFormat } from '../exporters';
import { pisoCodigoVisibleLabel, sortPisosByCodigo } from '../floorLabels';

type ActiveFilter = 'todos' | 'activos' | 'inactivos';
type UserRow = Record<string, unknown> & {
  id: string;
  apellidos: string;
  nombre: string;
  email: string;
  roles: string;
  estado: string;
  instituciones: string;
  complejos: string;
  torres: string;
  pisos: string;
};

const usuarios = ref<Usuario[]>([]);
const roles = ref<Role[]>([]);
const usuarioRoles = ref<UsuarioRol[]>([]);
const instituciones = ref<Institucion[]>([]);
const complejos = ref<Complejo[]>([]);
const torres = ref<Torre[]>([]);
const pisos = ref<Piso[]>([]);
const consultorios = ref<Consultorio[]>([]);
const medicos = ref<Medico[]>([]);
const operadores = ref<Operador[]>([]);
const asignacionesMedico = ref<AsignacionMedicoConsultorio[]>([]);
const asignacionesOperador = ref<AsignacionOperador[]>([]);
const institucionSearch = ref('');
const complejoSearch = ref('');
const torreSearch = ref('');
const pisoSearch = ref('');
const selectedInstitucionId = ref('');
const selectedComplejoId = ref('');
const selectedTorreId = ref('');
const selectedPisoId = ref('');
const selectedRoleId = ref('');
const activeFilter = ref<ActiveFilter>('todos');
const query = ref('');
const pageSize = ref(20);
const page = ref(1);
const error = ref('');
const loading = ref(false);

const filteredComplejos = computed(() =>
  selectedInstitucionId.value ? complejos.value.filter((item) => item.institucion_id === selectedInstitucionId.value) : complejos.value,
);

const filteredTorres = computed(() => {
  if (selectedComplejoId.value) return torres.value.filter((item) => item.complejo_id === selectedComplejoId.value);
  if (!selectedInstitucionId.value) return torres.value;
  const complejoIds = new Set(filteredComplejos.value.map((item) => item.id));
  return torres.value.filter((item) => complejoIds.has(item.complejo_id));
});

const filteredPisos = computed(() =>
  selectedTorreId.value ? sortPisosByCodigo(pisos.value.filter((item) => item.torre_id === selectedTorreId.value)) : [],
);

function institucionLabel(item: Institucion) {
  return item.razon_social ? `${item.nombre} · ${item.razon_social}` : item.nombre;
}

function pisoLabel(item: Piso) {
  return pisoCodigoVisibleLabel(item);
}

function torreLabel(item: Torre) {
  return item.nombre;
}

function matchByLabel<T>(rows: T[], text: string, labeler: (item: T) => string) {
  const normalized = text.trim().toLowerCase();
  return rows.find((item) => {
    const label = labeler(item).toLowerCase();
    return label === normalized || label.split(' · ')[0] === normalized || label.split(' - ')[0] === normalized;
  });
}

function syncInstitution() {
  selectedInstitucionId.value = matchByLabel(instituciones.value, institucionSearch.value, institucionLabel)?.id ?? '';
  if (!filteredComplejos.value.some((item) => item.id === selectedComplejoId.value)) {
    selectedComplejoId.value = '';
    complejoSearch.value = '';
  }
  if (!filteredTorres.value.some((item) => item.id === selectedTorreId.value)) {
    selectedTorreId.value = '';
    torreSearch.value = '';
  }
  if (!filteredPisos.value.some((item) => item.id === selectedPisoId.value)) {
    selectedPisoId.value = '';
    pisoSearch.value = '';
  }
}

function syncComplex() {
  selectedComplejoId.value = matchByLabel(filteredComplejos.value, complejoSearch.value, (item) => item.nombre)?.id ?? '';
  if (!filteredTorres.value.some((item) => item.id === selectedTorreId.value)) {
    selectedTorreId.value = '';
    torreSearch.value = '';
  }
  if (!filteredPisos.value.some((item) => item.id === selectedPisoId.value)) {
    selectedPisoId.value = '';
    pisoSearch.value = '';
  }
}

function syncTorre() {
  selectedTorreId.value = matchByLabel(filteredTorres.value, torreSearch.value, torreLabel)?.id ?? '';
  if (!filteredPisos.value.some((item) => item.id === selectedPisoId.value)) {
    selectedPisoId.value = '';
    pisoSearch.value = '';
  }
}

function syncPiso() {
  selectedPisoId.value = matchByLabel(filteredPisos.value, pisoSearch.value, pisoLabel)?.id ?? '';
}

function roleName(roleId: string) {
  const role = roles.value.find((item) => item.id === roleId);
  return role ? role.nombre || role.codigo : roleId;
}

function uniqueNames<T extends { id: string }>(ids: Set<string>, rows: T[], labeler: (row: T) => string) {
  return [...ids]
    .map((id) => rows.find((row) => row.id === id))
    .filter(Boolean)
    .map((row) => labeler(row as T))
    .sort();
}

function userScope(usuario: Usuario) {
  const roleRows = usuarioRoles.value.filter((item) => item.usuario_id === usuario.id && item.activo);
  const roleIds = new Set(roleRows.map((item) => item.rol_id));
  const institucionIds = new Set(roleRows.map((item) => item.institucion_id).filter(Boolean) as string[]);
  const complejoIds = new Set(roleRows.map((item) => item.complejo_id).filter(Boolean) as string[]);
  const torreIds = new Set(roleRows.map((item) => item.torre_id).filter(Boolean) as string[]);
  const pisoIds = new Set<string>();

  for (const roleRow of roleRows) {
    if (roleRow.torre_id) {
      const torre = torres.value.find((item) => item.id === roleRow.torre_id);
      if (torre) complejoIds.add(torre.complejo_id);
    }
    if (roleRow.piso_id) {
      const piso = pisos.value.find((item) => item.id === roleRow.piso_id);
      pisoIds.add(roleRow.piso_id);
      if (piso) torreIds.add(piso.torre_id);
    }
    if (roleRow.consultorio_id) {
      const consultorio = consultorios.value.find((item) => item.id === roleRow.consultorio_id);
      const piso = consultorio ? pisos.value.find((item) => item.id === consultorio.piso_id) : null;
      if (consultorio) {
        complejoIds.add(consultorio.complejo_id);
        pisoIds.add(consultorio.piso_id);
      }
      if (piso) torreIds.add(piso.torre_id);
    }
  }

  const medicoIds = medicos.value.filter((item) => item.usuario_id === usuario.id).map((item) => item.id);
  for (const asignacion of asignacionesMedico.value.filter((item) => medicoIds.includes(item.medico_id) && item.activo)) {
    const consultorio = consultorios.value.find((item) => item.id === asignacion.consultorio_id);
    const piso = consultorio ? pisos.value.find((item) => item.id === consultorio.piso_id) : null;
    if (consultorio) {
      complejoIds.add(consultorio.complejo_id);
      pisoIds.add(consultorio.piso_id);
    }
    if (piso) torreIds.add(piso.torre_id);
  }

  const operadorIds = operadores.value.filter((item) => item.usuario_id === usuario.id).map((item) => item.id);
  for (const asignacion of asignacionesOperador.value.filter((item) => operadorIds.includes(item.operador_id) && item.activo)) {
    complejoIds.add(asignacion.complejo_id);
    if (asignacion.consultorio_id) {
      const consultorio = consultorios.value.find((item) => item.id === asignacion.consultorio_id);
      const piso = consultorio ? pisos.value.find((item) => item.id === consultorio.piso_id) : null;
      if (consultorio) pisoIds.add(consultorio.piso_id);
      if (piso) torreIds.add(piso.torre_id);
    }
  }

  for (const pisoId of pisoIds) {
    const piso = pisos.value.find((item) => item.id === pisoId);
    if (piso) torreIds.add(piso.torre_id);
  }

  for (const torreId of torreIds) {
    const torre = torres.value.find((item) => item.id === torreId);
    if (torre) complejoIds.add(torre.complejo_id);
  }

  for (const complejoId of complejoIds) {
    const complejo = complejos.value.find((item) => item.id === complejoId);
    if (complejo) institucionIds.add(complejo.institucion_id);
  }

  return { roleIds, institucionIds, complejoIds, torreIds, pisoIds };
}

function medicoText(usuario: Usuario) {
  return medicos.value
    .filter((item) => item.usuario_id === usuario.id)
    .map((item) => `${item.nombre} ${item.apellidos} ${item.nombre_visible || ''}`)
    .join(' ');
}

function passesFilters(usuario: Usuario) {
  const scope = userScope(usuario);
  if (selectedRoleId.value && !scope.roleIds.has(selectedRoleId.value)) return false;
  if (selectedInstitucionId.value && !scope.institucionIds.has(selectedInstitucionId.value)) return false;
  if (selectedComplejoId.value && !scope.complejoIds.has(selectedComplejoId.value)) return false;
  if (selectedTorreId.value && !scope.torreIds.has(selectedTorreId.value)) return false;
  if (selectedPisoId.value && !scope.pisoIds.has(selectedPisoId.value)) return false;
  if (activeFilter.value !== 'todos') {
    const active = usuario.estado.toUpperCase() === 'ACTIVO';
    if (activeFilter.value === 'activos' && !active) return false;
    if (activeFilter.value === 'inactivos' && active) return false;
  }
  const terms = query.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
  if (!terms.length) return true;
  const haystack = `${usuario.apellidos} ${usuario.nombre} ${usuario.email} ${medicoText(usuario)}`.toLowerCase();
  return terms.every((term) => haystack.includes(term));
}

const filteredRows = computed<UserRow[]>(() =>
  usuarios.value.filter(passesFilters).map((usuario) => {
    const scope = userScope(usuario);
    return {
      id: usuario.id,
      apellidos: usuario.apellidos,
      nombre: usuario.nombre,
      email: usuario.email,
      roles: [...scope.roleIds].map(roleName).sort().join(', ') || '-',
      estado: usuario.estado,
      instituciones: uniqueNames(scope.institucionIds, instituciones.value, (item: Institucion) => item.nombre).join(', ') || '-',
      complejos: uniqueNames(scope.complejoIds, complejos.value, (item: Complejo) => item.nombre).join(', ') || '-',
      torres: uniqueNames(scope.torreIds, torres.value, (item: Torre) => item.nombre).join(', ') || '-',
      pisos: uniqueNames(scope.pisoIds, pisos.value, pisoLabel).join(', ') || '-',
    };
  }),
);

const totalPages = computed(() => Math.max(1, Math.ceil(filteredRows.value.length / pageSize.value)));
const pageRows = computed(() => filteredRows.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value));

const columns = [
  { key: 'apellidos', label: 'Apellido' },
  { key: 'nombre', label: 'Nombre' },
  { key: 'email', label: 'Correo' },
  { key: 'roles', label: 'Roles' },
  { key: 'estado', label: 'Estado' },
  { key: 'instituciones', label: 'Instituciones' },
  { key: 'complejos', label: 'Campus' },
  { key: 'torres', label: 'Torre' },
  { key: 'pisos', label: 'Pisos' },
];

async function loadData() {
  loading.value = true;
  error.value = '';
  try {
    const [
      usuariosData,
      rolesData,
      usuarioRolesData,
      institucionesData,
      complejosData,
      torresData,
      pisosData,
      consultoriosData,
      medicosData,
      operadoresData,
      asignacionesMedicoData,
      asignacionesOperadorData,
    ] = await Promise.all([
      listUsuarios(),
      listRoles(),
      listUsuarioRoles(),
      listInstituciones(),
      listComplejos(),
      listTorres(),
      listPisos(),
      listConsultorios(),
      listMedicos(),
      listOperadores(),
      listAsignacionesMedicoConsultorio(),
      listAsignacionesOperador(),
    ]);
    usuarios.value = usuariosData;
    roles.value = rolesData;
    usuarioRoles.value = usuarioRolesData;
    instituciones.value = institucionesData;
    complejos.value = complejosData;
    torres.value = torresData;
    pisos.value = pisosData;
    consultorios.value = consultoriosData;
    medicos.value = medicosData;
    operadores.value = operadoresData;
    asignacionesMedico.value = asignacionesMedicoData;
    asignacionesOperador.value = asignacionesOperadorData;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar usuarios.';
  } finally {
    loading.value = false;
  }
}

function clearFilters() {
  institucionSearch.value = '';
  complejoSearch.value = '';
  torreSearch.value = '';
  pisoSearch.value = '';
  selectedInstitucionId.value = '';
  selectedComplejoId.value = '';
  selectedTorreId.value = '';
  selectedPisoId.value = '';
  selectedRoleId.value = '';
  activeFilter.value = 'todos';
  query.value = '';
  page.value = 1;
}

function previousPage() {
  page.value = Math.max(1, page.value - 1);
}

function nextPage() {
  page.value = Math.min(totalPages.value, page.value + 1);
}

function exportUsers(format: ExportFormat) {
  exportRows(filteredRows.value, columns, 'busqueda-usuarios', format);
}

watch([filteredRows, pageSize], () => {
  page.value = Math.min(page.value, totalPages.value);
});

onMounted(loadData);
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Búsqueda de usuarios</h1>
        <p>Consulta de cuentas operativas por ubicación, rol, estado y nombre.</p>
      </div>
      <button class="secondary" type="button" @click="loadData">Actualizar</button>
    </header>

    <section class="panel form">
      <div class="form-grid">
        <div class="form-row">
          <label for="usuarios-institucion">Institución</label>
          <input id="usuarios-institucion" v-model="institucionSearch" list="usuarios-instituciones" @input="syncInstitution" @change="syncInstitution" />
          <datalist id="usuarios-instituciones">
            <option v-for="item in instituciones" :key="item.id" :value="institucionLabel(item)" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="usuarios-complejo">Campus</label>
          <input id="usuarios-complejo" v-model="complejoSearch" list="usuarios-complejos" @input="syncComplex" @change="syncComplex" />
          <datalist id="usuarios-complejos">
            <option v-for="item in filteredComplejos" :key="item.id" :value="item.nombre" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="usuarios-torre">Torre</label>
          <input id="usuarios-torre" v-model="torreSearch" list="usuarios-torres" @input="syncTorre" @change="syncTorre" />
          <datalist id="usuarios-torres">
            <option v-for="item in filteredTorres" :key="item.id" :value="torreLabel(item)" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="usuarios-piso">Piso</label>
          <input id="usuarios-piso" v-model="pisoSearch" :disabled="!selectedTorreId" list="usuarios-pisos" @input="syncPiso" @change="syncPiso" />
          <datalist id="usuarios-pisos">
            <option v-for="item in filteredPisos" :key="item.id" :value="pisoLabel(item)" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="usuarios-rol">Rol</label>
          <select id="usuarios-rol" v-model="selectedRoleId">
            <option value="">Todos</option>
            <option v-for="role in roles" :key="role.id" :value="role.id">{{ role.nombre || role.codigo }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="usuarios-activo">Estado</label>
          <select id="usuarios-activo" v-model="activeFilter">
            <option value="todos">Todos</option>
            <option value="activos">Activos</option>
            <option value="inactivos">Inactivos</option>
          </select>
        </div>
        <div class="form-row">
          <label for="usuarios-busqueda">Nombre</label>
          <input id="usuarios-busqueda" v-model="query" placeholder="Nombre o apellido" />
        </div>
      </div>
      <div class="actions-row">
        <button type="button" @click="page = 1">Filtrar</button>
        <button class="secondary" type="button" @click="clearFilters">Limpiar</button>
        <button class="secondary" type="button" @click="exportUsers('excel')">Excel</button>
        <button class="secondary" type="button" @click="exportUsers('csv')">CSV</button>
        <button class="secondary" type="button" @click="exportUsers('json')">JSON</button>
      </div>
    </section>

    <section class="panel table-panel">
      <div class="page-header compact">
        <div>
          <h2>{{ filteredRows.length }} usuarios</h2>
          <p>Página {{ page }} de {{ totalPages }}</p>
        </div>
        <div class="inline-actions">
          <select v-model.number="pageSize">
            <option :value="20">20</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
          </select>
          <button class="secondary" type="button" :disabled="page <= 1" @click="previousPage">Anterior</button>
          <button class="secondary" type="button" :disabled="page >= totalPages" @click="nextPage">Siguiente</button>
        </div>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="loading" class="message">Cargando...</p>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th v-for="column in columns" :key="column.key">{{ column.label }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in pageRows" :key="row.id">
              <td v-for="column in columns" :key="column.key">{{ row[column.key] }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="!loading && pageRows.length === 0" class="message">No hay usuarios para mostrar.</p>
    </section>
  </section>
</template>
