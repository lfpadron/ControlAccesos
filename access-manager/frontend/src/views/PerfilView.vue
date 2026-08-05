<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { changeMyPassword, getCurrentUser, updateMyProfile, type Usuario } from '../api/client';

const profile = ref<Usuario | null>(null);
const correoAlterno = ref('');
const currentPassword = ref('');
const newPassword = ref('');
const confirmPassword = ref('');
const profileError = ref('');
const profileSuccess = ref('');
const passwordError = ref('');
const passwordSuccess = ref('');
const profileLoading = ref(false);
const passwordLoading = ref(false);
const passwordRequirementsMessage = 'La contraseña debe tener al menos 8 caracteres y al menos 1 número.';
const roleText = computed(() => profile.value?.roles?.join(', ') || 'Sin rol asignado');

async function loadProfile() {
  profileError.value = '';
  try {
    profile.value = await getCurrentUser();
    correoAlterno.value = profile.value.correo_alterno ?? '';
  } catch (err) {
    profileError.value = err instanceof Error ? err.message : 'No fue posible cargar su perfil.';
  }
}

async function submitProfile() {
  profileError.value = '';
  profileSuccess.value = '';
  profileLoading.value = true;
  try {
    profile.value = await updateMyProfile({
      correo_alterno: correoAlterno.value.trim() || null,
    });
    correoAlterno.value = profile.value.correo_alterno ?? '';
    profileSuccess.value = 'Perfil actualizado correctamente.';
    window.dispatchEvent(new CustomEvent('current-user-updated'));
  } catch (err) {
    profileError.value = err instanceof Error ? err.message : 'No fue posible actualizar su perfil.';
  } finally {
    profileLoading.value = false;
  }
}

async function submitPasswordChange() {
  passwordError.value = '';
  passwordSuccess.value = '';
  if (newPassword.value.length < 8 || !/\d/.test(newPassword.value)) {
    passwordError.value = passwordRequirementsMessage;
    return;
  }
  if (newPassword.value !== confirmPassword.value) {
    passwordError.value = 'La confirmación de contraseña no coincide.';
    return;
  }
  passwordLoading.value = true;
  try {
    profile.value = await changeMyPassword({
      current_password: currentPassword.value,
      new_password: newPassword.value,
    });
    correoAlterno.value = profile.value.correo_alterno ?? '';
    currentPassword.value = '';
    newPassword.value = '';
    confirmPassword.value = '';
    passwordSuccess.value = 'Contraseña actualizada correctamente.';
    window.dispatchEvent(new CustomEvent('current-user-updated'));
  } catch (err) {
    passwordError.value = err instanceof Error ? err.message : 'No fue posible cambiar la contraseña.';
  } finally {
    passwordLoading.value = false;
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
      <form class="panel form compact-form" autocomplete="off" @submit.prevent="submitProfile">
        <h2>Datos de usuario</h2>
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
            <dt>Rol</dt>
            <dd>{{ roleText }}</dd>
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
        <div class="form-row">
          <label for="correo-alterno">Correo alterno</label>
          <input id="correo-alterno" v-model="correoAlterno" type="email" autocomplete="email" maxlength="255" />
        </div>
        <p v-if="profileError" class="error">{{ profileError }}</p>
        <p v-if="profileSuccess" class="success-message">{{ profileSuccess }}</p>
        <button type="submit" :disabled="profileLoading">{{ profileLoading ? 'Guardando...' : 'Actualizar perfil' }}</button>
      </form>

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
        <p v-if="passwordError" class="error">{{ passwordError }}</p>
        <p v-if="passwordSuccess" class="success-message">{{ passwordSuccess }}</p>
        <button type="submit" :disabled="passwordLoading">{{ passwordLoading ? 'Guardando...' : 'Actualizar contraseña' }}</button>
      </form>
    </div>
  </section>
</template>
