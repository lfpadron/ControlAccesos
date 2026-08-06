<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { accessLevels, screens } from '../accessControl';
import { activateResource, createRole, deactivateResource, listRoles, updateRole, type AccessLevel, type Role } from '../api/client';

const roles = ref<Role[]>([]);
const selected = ref<Role | null>(null);
const creating = ref(false);
const loading = ref(false);
const error = ref('');
const message = ref('');

const form = reactive({
  codigo: '',
  nombre: '',
  descripcion: '',
  activo: true,
  permisos: {} as Record<string, AccessLevel>,
});

const canEditForm = computed(() => creating.value || selected.value !== null);
const formTitle = computed(() => {
  if (creating.value) return 'Crear rol';
  return selected.value ? `Permisos de ${selected.value.nombre}` : 'Seleccione un rol';
});

function blankPermissions() {
  return Object.fromEntries(screens.map((screen) => [screen.key, 'sin' as AccessLevel]));
}

function defaultPermissions(role: Role | null) {
  if (role?.codigo === 'ADMIN_SISTEMA') {
    return Object.fromEntries(screens.map((screen) => [screen.key, 'editar' as AccessLevel]));
  }
  return blankPermissions();
}

function setForm(role: Role | null) {
  selected.value = role;
  creating.value = false;
  form.codigo = role?.codigo ?? '';
  form.nombre = role?.nombre ?? '';
  form.descripcion = role?.descripcion ?? '';
  form.activo = role?.activo ?? true;
  form.permisos = role ? { ...defaultPermissions(role), ...(role.permisos ?? {}) } : {};
  message.value = '';
  error.value = '';
}

function newRole() {
  selected.value = null;
  creating.value = true;
  form.codigo = '';
  form.nombre = '';
  form.descripcion = '';
  form.activo = true;
  form.permisos = blankPermissions();
  message.value = '';
  error.value = '';
}

async function loadData() {
  loading.value = true;
  error.value = '';
  try {
    roles.value = await listRoles();
    if (selected.value) {
      const refreshed = roles.value.find((role) => role.id === selected.value?.id) ?? null;
      setForm(refreshed);
    }
    if (!selected.value && !creating.value) {
      setForm(null);
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar roles.';
  } finally {
    loading.value = false;
  }
}

async function submit() {
  if (!canEditForm.value) return;
  loading.value = true;
  error.value = '';
  message.value = '';
  const payload = {
    codigo: form.codigo.trim(),
    nombre: form.nombre.trim(),
    descripcion: form.descripcion.trim() || null,
    permisos: form.permisos,
    activo: form.activo,
  };
  try {
    if (creating.value) {
      const created = await createRole(payload);
      creating.value = false;
      selected.value = created;
      message.value = 'Rol creado.';
    } else if (selected.value) {
      await updateRole(selected.value.id, payload);
      message.value = 'Rol actualizado.';
    }
    await loadData();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible guardar el rol.';
  } finally {
    loading.value = false;
  }
}

async function setActive(role: Role, active: boolean) {
  loading.value = true;
  error.value = '';
  message.value = '';
  try {
    await (active ? activateResource<Role>('roles', role.id) : deactivateResource<Role>('roles', role.id));
    message.value = active ? 'Rol activado.' : 'Rol desactivado.';
    await loadData();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cambiar el estado del rol.';
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
        <h1>Roles</h1>
        <p>Permisos por pantalla para cada rol existente.</p>
      </div>
    </header>

    <div class="grid catalog-grid">
      <section class="panel table-panel">
        <div class="actions-row">
          <h2>Roles actuales</h2>
          <button type="button" @click="newRole">+ Nuevo rol</button>
        </div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Código</th>
                <th>Nombre</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="role in roles" :key="role.id" class="selectable-row" :class="{ selected: selected?.id === role.id }" @click="setForm(role)">
                <td>{{ role.codigo }}</td>
                <td>{{ role.nombre }}</td>
                <td>{{ role.activo ? 'Activo' : 'Inactivo' }}</td>
                <td>
                  <button v-if="role.activo" class="small danger" type="button" :disabled="loading" @click.stop="setActive(role, false)">Desactivar</button>
                  <button v-else class="small secondary" type="button" :disabled="loading" @click.stop="setActive(role, true)">Activar</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <form class="panel form" @submit.prevent="submit">
        <h2>{{ formTitle }}</h2>
        <template v-if="canEditForm">
          <div class="form-grid">
            <div class="form-row">
              <label for="role-code">Código</label>
              <input id="role-code" v-model="form.codigo" required maxlength="80" />
            </div>
            <div class="form-row">
              <label for="role-name">Nombre</label>
              <input id="role-name" v-model="form.nombre" required maxlength="180" />
            </div>
          </div>
          <div class="form-row">
            <label for="role-description">Descripción</label>
            <textarea id="role-description" v-model="form.descripcion" rows="3" />
          </div>
          <label class="check-row">
            <input v-model="form.activo" type="checkbox" />
            Activo
          </label>

          <div class="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Pantalla</th>
                  <th v-for="level in accessLevels" :key="level.value">{{ level.label }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="screen in screens" :key="screen.key">
                  <td>{{ screen.label }}</td>
                  <td v-for="level in accessLevels" :key="`${screen.key}-${level.value}`">
                    <label class="check-row">
                      <input v-model="form.permisos[screen.key]" type="radio" :name="`perm-${screen.key}`" :value="level.value" />
                      {{ level.label }}
                    </label>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <p v-if="message" class="message">{{ message }}</p>
          <p v-if="error" class="error">{{ error }}</p>
          <div class="actions-row">
            <button type="submit" :disabled="loading">{{ loading ? 'Guardando...' : '✓ Guardar' }}</button>
            <button class="secondary" type="button" @click="setForm(null)">Cancelar</button>
          </div>
        </template>
        <p v-else class="message">Seleccione un rol para editar sus permisos o cree uno nuevo.</p>
      </form>
    </div>
  </section>
</template>
