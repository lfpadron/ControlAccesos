<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router';
import { clearToken, getCurrentUser, getToken, type Usuario } from './api/client';
import astrogatoLogo from './astrogato-logo.png';
import clinicasLogo from './clinicas-alfa.png';

const router = useRouter();
const route = useRoute();
const fullscreen = computed(() => Boolean(route.meta.fullscreen));
const currentUser = ref<Usuario | null>(null);
const showUserBadge = computed(() => Boolean(getToken() && currentUser.value && !fullscreen.value && !route.meta.hideUserBadge));
const footerTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'America/Mexico_City';
const footerClockFormatter = new Intl.DateTimeFormat('es-MX', {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
  timeZone: footerTimeZone,
});
const footerDate = ref(new Date());
const footerClock = computed(() => footerClockFormatter.format(footerDate.value));
const footerDatetime = computed(() => footerDate.value.toISOString());

let footerClockTimer: number | undefined;

async function refreshCurrentUser() {
  if (!getToken() || fullscreen.value) {
    currentUser.value = null;
    return;
  }
  try {
    currentUser.value = await getCurrentUser();
  } catch {
    currentUser.value = null;
  }
}

function handleCurrentUserUpdated() {
  void refreshCurrentUser();
}

onMounted(() => {
  footerDate.value = new Date();
  footerClockTimer = window.setInterval(() => {
    footerDate.value = new Date();
  }, 1000);
  window.addEventListener('current-user-updated', handleCurrentUserUpdated);
});

onUnmounted(() => {
  window.clearInterval(footerClockTimer);
  window.removeEventListener('current-user-updated', handleCurrentUserUpdated);
});

function logout() {
  clearToken();
  currentUser.value = null;
  router.push('/login');
}

watch(
  () => route.fullPath,
  () => {
    void refreshCurrentUser();
  },
  { immediate: true },
);
</script>

<template>
  <div v-if="fullscreen" class="fullscreen-frame">
    <RouterView v-if="fullscreen" />
    <footer class="app-footer">
      <span class="app-footer-mission">UNA MISIÓN EN PROGRESO DE:</span>
      <img class="app-footer-logo" :src="astrogatoLogo" alt="Astrogato Labs" />
      <span class="app-footer-clock">
        Zona horaria: {{ footerTimeZone }} · <time :datetime="footerDatetime">{{ footerClock }}</time>
      </span>
    </footer>
  </div>
  <div v-else class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <img class="brand-logo" :src="clinicasLogo" alt="Clínicas Alfa" />
        <div>
          <strong>Control de acceso</strong>
          <small>Clínicas Alfa</small>
        </div>
      </div>
      <nav>
        <span class="nav-section">General</span>
        <RouterLink to="/dashboard">Dashboard</RouterLink>
        <RouterLink to="/perfil">Perfil</RouterLink>
        <span class="nav-section">Instituciones</span>
        <RouterLink to="/instituciones">Instituciones</RouterLink>
        <RouterLink to="/complejos">Complejos</RouterLink>
        <RouterLink to="/pisos">Pisos</RouterLink>
        <RouterLink to="/salas-espera">Salas de espera</RouterLink>
        <RouterLink to="/clusters-turnos">Clústers</RouterLink>
        <RouterLink to="/consultorios">Consultorios</RouterLink>
        <span class="nav-section">Personas y roles</span>
        <RouterLink to="/usuarios">Usuarios</RouterLink>
        <RouterLink to="/busqueda-usuarios">Búsqueda de usuarios</RouterLink>
        <RouterLink to="/roles">Roles</RouterLink>
        <RouterLink to="/usuario-roles">Roles de usuario</RouterLink>
        <RouterLink to="/medicos">Médicos</RouterLink>
        <RouterLink to="/operadores">Operadores</RouterLink>
        <span class="nav-section">Operación</span>
        <RouterLink to="/pacientes">Pacientes</RouterLink>
        <RouterLink to="/citas">Citas</RouterLink>
        <RouterLink to="/citas/hoy">Citas de hoy</RouterLink>
        <RouterLink to="/contactos-institucionales">Contactos institucionales</RouterLink>
        <RouterLink to="/asignaciones">Asignaciones</RouterLink>
        <RouterLink to="/pantallas-turnos">Pantallas de turnos</RouterLink>
        <RouterLink to="/kioskos">Kioskos</RouterLink>
        <RouterLink to="/turnos-llamados">Turnos llamados</RouterLink>
        <RouterLink to="/reportes">Reportes</RouterLink>
        <RouterLink to="/auditoria">Auditoría</RouterLink>
      </nav>
      <button v-if="getToken()" class="secondary" type="button" @click="logout">Cerrar sesión</button>
    </aside>
    <main class="content">
      <div v-if="showUserBadge" class="user-badge-row">
        <RouterLink class="user-badge" to="/perfil">
          <span>Usuario</span>
          <strong>{{ currentUser?.nombre }}</strong>
          <em v-if="currentUser?.force_password_change">Cambio de contraseña pendiente</em>
        </RouterLink>
      </div>
      <RouterView />
    </main>
    <footer class="app-footer">
      <span class="app-footer-mission">UNA MISIÓN EN PROGRESO DE:</span>
      <img class="app-footer-logo" :src="astrogatoLogo" alt="Astrogato Labs" />
      <span class="app-footer-clock">
        Zona horaria: {{ footerTimeZone }} · <time :datetime="footerDatetime">{{ footerClock }}</time>
      </span>
    </footer>
  </div>
</template>
