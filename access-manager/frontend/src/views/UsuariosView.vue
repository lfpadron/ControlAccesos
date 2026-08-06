<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import {
  createUsuario,
  createUsuarioRol,
  listRoles,
  listUsuarioRoles,
  listUsuarios,
  updateUsuario,
  updateUsuarioRol,
  type Role,
  type Usuario,
  type UsuarioRol,
} from '../api/client';

const PAGE_SIZE = 20;

const usuarios = ref<Usuario[]>([]);
const roles = ref<Role[]>([]);
const usuarioRoles = ref<UsuarioRol[]>([]);
const selected = ref<Usuario | null>(null);
const loading = ref(false);
const error = ref('');
const message = ref('');
const page = ref(1);

const filters = reactive({
  q: '',
  rol_id: '',
});

const appliedFilters = reactive({
  q: '',
  rol_id: '',
});

const form = reactive({
  nombre: '',
  email: '',
  correo_alterno: '',
  password: '',
  telefono: '',
  rol_id: '',
  force_password_change: false,
  estado: 'ACTIVO',
});

const filteredUsers = computed(() => {
  const q = appliedFilters.q.trim().toLowerCase();
  return usuarios.value.filter((user) => {
    if (q) {
      const haystack = [user.nombre, user.email, user.correo_alterno ?? ''].join(' ').toLowerCase();
      if (!haystack.includes(q)) return false;
    }
    if (appliedFilters.rol_id && !rolesForUser(user.id).some((item) => item.rol_id === appliedFilters.rol_id && item.activo)) {
      return false;
    }
    return true;
  });
});

const totalPages = computed(() => Math.max(1, Math.ceil(filteredUsers.value.length / PAGE_SIZE)));
const paginatedUsers = computed(() => filteredUsers.value.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE));

function roleLabel(id: string) {
  const role = roles.value.find((item) => item.id === id);
  return role ? role.nombre || role.codigo : 'Sin rol';
}

function rolesForUser(userId: string) {
  return usuarioRoles.value.filter((item) => item.usuario_id === userId);
}

function roleText(userId: string) {
  const labels = rolesForUser(userId)
    .filter((item) => item.activo)
    .map((item) => roleLabel(item.rol_id));
  return labels.length ? labels.join(', ') : 'Sin rol asignado';
}

function resetForm() {
  selected.value = null;
  form.nombre = '';
  form.email = '';
  form.correo_alterno = '';
  form.password = '';
  form.telefono = '';
  form.rol_id = '';
  form.force_password_change = false;
  form.estado = 'ACTIVO';
}

function editUser(user: Usuario) {
  selected.value = user;
  form.nombre = user.nombre;
  form.email = user.email;
  form.correo_alterno = user.correo_alterno ?? '';
  form.password = '';
  form.telefono = user.telefono ?? '';
  form.rol_id = rolesForUser(user.id).find((item) => item.activo)?.rol_id ?? '';
  form.force_password_change = user.force_password_change;
  form.estado = user.estado;
}

function applyFilters() {
  appliedFilters.q = filters.q;
  appliedFilters.rol_id = filters.rol_id;
  page.value = 1;
}

function clearFilters() {
  filters.q = '';
  filters.rol_id = '';
  applyFilters();
}

async function loadData() {
  loading.value = true;
  error.value = '';
  try {
    const [usersData, rolesData, userRolesData] = await Promise.all([listUsuarios(), listRoles(), listUsuarioRoles()]);
    usuarios.value = usersData;
    roles.value = rolesData;
    usuarioRoles.value = userRolesData;
    if (page.value > totalPages.value) page.value = totalPages.value;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar usuarios.';
  } finally {
    loading.value = false;
  }
}

async function assignSingleRole(userId: string, roleId: string) {
  const assignments = rolesForUser(userId);
  let selectedAssignment = assignments.find((item) => item.rol_id === roleId);
  for (const assignment of assignments) {
    if (assignment.rol_id !== roleId && assignment.activo) {
      await updateUsuarioRol(assignment.id, { activo: false });
    }
  }
  if (selectedAssignment) {
    if (!selectedAssignment.activo) {
      await updateUsuarioRol(selectedAssignment.id, { activo: true });
    }
  } else {
    await createUsuarioRol({ usuario_id: userId, rol_id: roleId, activo: true });
  }
}

async function submit() {
  error.value = '';
  message.value = '';
  if (!form.rol_id) {
    error.value = 'Debe asignar un rol al usuario.';
    return;
  }
  loading.value = true;
  try {
    const payload: Record<string, unknown> = {
      nombre: form.nombre.trim(),
      email: form.email.trim(),
      correo_alterno: form.correo_alterno.trim() || null,
      telefono: form.telefono.trim() || null,
      force_password_change: form.force_password_change,
      estado: form.estado,
    };
    if (!selected.value || form.password.trim()) {
      payload.password = form.password;
    }
    const saved = selected.value ? await updateUsuario(selected.value.id, payload) : await createUsuario(payload);
    await assignSingleRole(saved.id, form.rol_id);
    message.value = selected.value ? 'Usuario actualizado.' : 'Usuario creado.';
    await loadData();
    resetForm();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible guardar el usuario.';
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
        <h1>Usuarios</h1>
        <p>Cuentas de acceso con rol obligatorio.</p>
      </div>
    </header>

    <section class="panel">
      <div class="form-grid">
        <div class="form-row">
          <label for="usuario-q">Nombre o correos</label>
          <input id="usuario-q" v-model="filters.q" @keyup.enter="applyFilters" />
        </div>
        <div class="form-row">
          <label for="usuario-rol-filter">Rol</label>
          <select id="usuario-rol-filter" v-model="filters.rol_id">
            <option value="">Todos los roles</option>
            <option v-for="role in roles" :key="role.id" :value="role.id">{{ role.nombre || role.codigo }}</option>
          </select>
        </div>
      </div>
      <div class="actions-row">
        <button type="button" @click="applyFilters">Buscar</button>
        <button class="secondary" type="button" @click="clearFilters">Limpiar</button>
      </div>
    </section>

    <div class="grid catalog-grid">
      <form class="panel form" autocomplete="off" @submit.prevent="submit">
        <h2>{{ selected ? 'Editar usuario' : 'Crear usuario' }}</h2>
        <div class="form-row">
          <label for="usuario-nombre">Nombre</label>
          <input id="usuario-nombre" v-model="form.nombre" required maxlength="180" />
        </div>
        <div class="form-row">
          <label for="usuario-email">Correo electrónico</label>
          <input id="usuario-email" v-model="form.email" required type="email" maxlength="255" />
        </div>
        <div class="form-row">
          <label for="usuario-correo-alterno">Correo alterno</label>
          <input id="usuario-correo-alterno" v-model="form.correo_alterno" type="email" maxlength="255" />
        </div>
        <div class="form-row">
          <label for="usuario-password">Contraseña temporal / nueva</label>
          <input id="usuario-password" v-model="form.password" type="password" :required="!selected" minlength="8" maxlength="128" autocomplete="new-password" />
        </div>
        <div class="form-row">
          <label for="usuario-telefono">Teléfono</label>
          <input id="usuario-telefono" v-model="form.telefono" maxlength="64" />
        </div>
        <div class="form-row">
          <label for="usuario-rol">Rol</label>
          <select id="usuario-rol" v-model="form.rol_id" required>
            <option value="">Seleccione rol</option>
            <option v-for="role in roles" :key="role.id" :value="role.id">{{ role.nombre || role.codigo }}</option>
          </select>
        </div>
        <div class="form-row">
          <label for="usuario-estado">Estado</label>
          <select id="usuario-estado" v-model="form.estado">
            <option value="ACTIVO">Activo</option>
            <option value="INACTIVO">Inactivo</option>
          </select>
        </div>
        <label class="check-row">
          <input v-model="form.force_password_change" type="checkbox" />
          Forzar cambio de contraseña
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
                <th>Nombre</th>
                <th>Correo</th>
                <th>Correo alterno</th>
                <th>Rol</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in paginatedUsers" :key="user.id" class="selectable-row" :class="{ selected: selected?.id === user.id }" @click="editUser(user)">
                <td>{{ user.nombre }}</td>
                <td>{{ user.email }}</td>
                <td>{{ user.correo_alterno || '-' }}</td>
                <td>{{ roleText(user.id) }}</td>
                <td>{{ user.estado }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="!loading && filteredUsers.length === 0" class="message">No hay usuarios para mostrar.</p>
        <div class="actions-row">
          <button class="secondary" type="button" :disabled="page <= 1" @click="page -= 1">Anterior</button>
          <span class="message">Página {{ page }} de {{ totalPages }}</span>
          <button class="secondary" type="button" :disabled="page >= totalPages" @click="page += 1">Siguiente</button>
        </div>
      </section>
    </div>
  </section>
</template>
