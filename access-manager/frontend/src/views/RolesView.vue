<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { accessLevels, screens } from '../accessControl';
import { listRoles, updateRole, type AccessLevel, type Role } from '../api/client';

const roles = ref<Role[]>([]);
const selected = ref<Role | null>(null);
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

function defaultPermissions(role: Role) {
  if (role.codigo === 'ADMIN_SISTEMA') {
    return Object.fromEntries(screens.map((screen) => [screen.key, 'editar' as AccessLevel]));
  }
  return Object.fromEntries(screens.map((screen) => [screen.key, 'sin' as AccessLevel]));
}

function setForm(role: Role | null) {
  selected.value = role;
  form.codigo = role?.codigo ?? '';
  form.nombre = role?.nombre ?? '';
  form.descripcion = role?.descripcion ?? '';
  form.activo = role?.activo ?? true;
  form.permisos = role ? { ...defaultPermissions(role), ...(role.permisos ?? {}) } : {};
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
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar roles.';
  } finally {
    loading.value = false;
  }
}

async function submit() {
  if (!selected.value) return;
  loading.value = true;
  error.value = '';
  message.value = '';
  try {
    await updateRole(selected.value.id, {
      codigo: form.codigo.trim(),
      nombre: form.nombre.trim(),
      descripcion: form.descripcion.trim() || null,
      permisos: form.permisos,
      activo: form.activo,
    });
    message.value = 'Rol actualizado.';
    await loadData();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible guardar el rol.';
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
        <h2>Roles actuales</h2>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Código</th>
                <th>Nombre</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="role in roles" :key="role.id" class="selectable-row" :class="{ selected: selected?.id === role.id }" @click="setForm(role)">
                <td>{{ role.codigo }}</td>
                <td>{{ role.nombre }}</td>
                <td>{{ role.activo ? 'Activo' : 'Inactivo' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <form class="panel form" @submit.prevent="submit">
        <h2>{{ selected ? `Permisos de ${selected.nombre}` : 'Seleccione un rol' }}</h2>
        <template v-if="selected">
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
          </div>
        </template>
        <p v-else class="message">Seleccione un rol para editar sus permisos.</p>
      </form>
    </div>
  </section>
</template>
