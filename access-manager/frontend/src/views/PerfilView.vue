<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { changeMyPassword, getCurrentUser, type Usuario } from '../api/client';

const profile = ref<Usuario | null>(null);
const currentPassword = ref('');
const newPassword = ref('');
const confirmPassword = ref('');
const error = ref('');
const success = ref('');
const loading = ref(false);
const passwordRequirementsMessage = 'La contraseña debe tener al menos 8 caracteres y al menos 1 número.';

async function loadProfile() {
  error.value = '';
  try {
    profile.value = await getCurrentUser();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar su perfil.';
  }
}

async function submitPasswordChange() {
  error.value = '';
  success.value = '';
  if (newPassword.value.length < 8 || !/\d/.test(newPassword.value)) {
    error.value = passwordRequirementsMessage;
    return;
  }
  if (newPassword.value !== confirmPassword.value) {
    error.value = 'La confirmación de contraseña no coincide.';
    return;
  }
  loading.value = true;
  try {
    profile.value = await changeMyPassword({
      current_password: currentPassword.value,
      new_password: newPassword.value,
    });
    currentPassword.value = '';
    newPassword.value = '';
    confirmPassword.value = '';
    success.value = 'Contraseña actualizada correctamente.';
    window.dispatchEvent(new CustomEvent('current-user-updated'));
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cambiar la contraseña.';
  } finally {
    loading.value = false;
  }
}

onMounted(loadProfile);
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Perfil</h1>
        <p>Consulte sus datos de acceso y cambie su contraseña.</p>
      </div>
    </header>

    <div class="grid profile-grid">
      <section class="panel">
        <h2>Datos de usuario</h2>
        <p class="message">Para cambios en su perfil, favor de dirigirse con su administrador.</p>
        <dl v-if="profile" class="profile-list">
          <div>
            <dt>Nombre</dt>
            <dd>{{ profile.nombre }}</dd>
          </div>
          <div>
            <dt>Correo</dt>
            <dd>{{ profile.email }}</dd>
          </div>
          <div>
            <dt>Teléfono</dt>
            <dd>{{ profile.telefono || 'Sin capturar' }}</dd>
          </div>
          <div>
            <dt>Estado</dt>
            <dd>{{ profile.estado }}</dd>
          </div>
        </dl>
      </section>

      <form class="panel form compact-form" autocomplete="off" @submit.prevent="submitPasswordChange">
        <h2>Cambiar contraseña</h2>
        <p v-if="profile?.force_password_change" class="warning">Debe cambiar su contraseña antes de continuar.</p>
        <div class="form-row">
          <label for="current-password">Contraseña actual</label>
          <input
            id="current-password"
            v-model="currentPassword"
            type="password"
            autocomplete="current-password"
            required
          />
        </div>
        <div class="form-row">
          <label for="new-password">Nueva contraseña</label>
          <input
            id="new-password"
            v-model="newPassword"
            type="password"
            autocomplete="new-password"
            minlength="8"
            maxlength="128"
            pattern="^(?=.*\d).{8,128}$"
            :title="passwordRequirementsMessage"
            required
          />
        </div>
        <div class="form-row">
          <label for="confirm-password">Confirmar nueva contraseña</label>
          <input
            id="confirm-password"
            v-model="confirmPassword"
            type="password"
            autocomplete="new-password"
            minlength="8"
            maxlength="128"
            pattern="^(?=.*\d).{8,128}$"
            :title="passwordRequirementsMessage"
            required
          />
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <p v-if="success" class="success-message">{{ success }}</p>
        <button type="submit" :disabled="loading">{{ loading ? 'Guardando...' : 'Actualizar contraseña' }}</button>
      </form>
    </div>
  </section>
</template>
