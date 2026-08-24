<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { getCurrentUser, login } from '../api/client';
import { initialPathForUser } from '../accessControl';
import { setCurrentSessionUser, setSessionToken } from '../authSession';

const router = useRouter();
const email = ref('admin1@example.com');
const password = ref('');
const error = ref('');
const loading = ref(false);

async function submit() {
  error.value = '';
  loading.value = true;
  try {
    const response = await login(email.value.trim(), password.value);
    setSessionToken(response.access_token);
    const user = await getCurrentUser();
    setCurrentSessionUser(user);
    await router.push(user.force_password_change ? '/perfil' : initialPathForUser(user));
    window.dispatchEvent(new CustomEvent('current-user-updated', { detail: user }));
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible iniciar sesión.';
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-shell">
    <section class="panel login-panel">
      <div class="page-header">
        <div>
          <h1>Iniciar sesión</h1>
          <p>Acceso administrativo para torres y campus.</p>
        </div>
      </div>
      <form class="form" @submit.prevent="submit">
        <div class="form-row">
          <label for="email">Email</label>
          <input id="email" v-model="email" type="email" autocomplete="email" required />
        </div>
        <div class="form-row">
          <label for="password">Contraseña</label>
          <input id="password" v-model="password" type="password" autocomplete="current-password" required />
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <button type="submit" :disabled="loading">{{ loading ? 'Validando...' : 'Entrar' }}</button>
      </form>
    </section>
  </div>
</template>
