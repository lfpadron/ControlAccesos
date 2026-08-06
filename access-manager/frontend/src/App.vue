<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router';
import { clearToken, getCurrentUser, getToken, type Usuario } from './api/client';
import { canAccessPath } from './accessControl';
import astrogatoLogo from './astrogato-logo-v02.png';
import capitalHeaderLogo from './capital-logo-encabezado.png';
import capitalMenuLogo from './capital-logo-menu.png';
import { useLocationContext } from './composables/useLocationContext';

const router = useRouter();
const route = useRoute();
const fullscreen = computed(() => Boolean(route.meta.fullscreen));
const currentUser = ref<Usuario | null>(null);
const { clearCampus, clearFloor, clearLocation, clearTower } = useLocationContext();
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

function canUse(path: string) {
  return canAccessPath(currentUser.value, path);
}

function handleNav(event: MouseEvent, path: string, reset?: () => void) {
  if (!canUse(path)) {
    event.preventDefault();
    return;
  }
  reset?.();
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
      <a class="app-footer-link" href="https://astrogatolabs.com.mx/" target="_blank" rel="noopener noreferrer">
        <img class="app-footer-logo" :src="astrogatoLogo" alt="Astrogato Labs" />
      </a>
      <span class="app-footer-clock">
        Zona horaria: {{ footerTimeZone }} · <time :datetime="footerDatetime">{{ footerClock }}</time>
      </span>
    </footer>
  </div>
  <div v-else class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <img class="brand-logo" :src="capitalMenuLogo" alt="Capital Medical Center" />
        <div>
          <strong>Control de acceso</strong>
          <small>Capital Medical Center</small>
        </div>
      </div>
      <nav>
        <span class="nav-section">General</span>
        <RouterLink to="/dashboard" :class="{ disabled: !canUse('/dashboard') }" :aria-disabled="!canUse('/dashboard')" @click="handleNav($event, '/dashboard')">Dashboard</RouterLink>
        <RouterLink to="/perfil" :class="{ disabled: !canUse('/perfil') }" :aria-disabled="!canUse('/perfil')" @click="handleNav($event, '/perfil')">Perfil</RouterLink>
        <span class="nav-section">Instituciones</span>
        <RouterLink to="/instituciones" :class="{ disabled: !canUse('/instituciones') }" :aria-disabled="!canUse('/instituciones')" @click="handleNav($event, '/instituciones', clearLocation)">Instituciones</RouterLink>
        <RouterLink to="/complejos" :class="{ disabled: !canUse('/complejos') }" :aria-disabled="!canUse('/complejos')" @click="handleNav($event, '/complejos', clearCampus)">Campus</RouterLink>
        <RouterLink to="/torres" :class="{ disabled: !canUse('/torres') }" :aria-disabled="!canUse('/torres')" @click="handleNav($event, '/torres', clearTower)">Torres</RouterLink>
        <RouterLink to="/pisos" :class="{ disabled: !canUse('/pisos') }" :aria-disabled="!canUse('/pisos')" @click="handleNav($event, '/pisos', clearFloor)">Pisos</RouterLink>
        <RouterLink to="/salas-espera" :class="{ disabled: !canUse('/salas-espera') }" :aria-disabled="!canUse('/salas-espera')" @click="handleNav($event, '/salas-espera')">Salas de espera</RouterLink>
        <RouterLink to="/clusters-turnos" :class="{ disabled: !canUse('/clusters-turnos') }" :aria-disabled="!canUse('/clusters-turnos')" @click="handleNav($event, '/clusters-turnos')">Clústers</RouterLink>
        <RouterLink to="/consultorios" :class="{ disabled: !canUse('/consultorios') }" :aria-disabled="!canUse('/consultorios')" @click="handleNav($event, '/consultorios')">Consultorios</RouterLink>
        <RouterLink to="/consulta-clusters-consultorios" :class="{ disabled: !canUse('/consulta-clusters-consultorios') }" :aria-disabled="!canUse('/consulta-clusters-consultorios')" @click="handleNav($event, '/consulta-clusters-consultorios')">Consulta de clústers</RouterLink>
        <span class="nav-section">Personas y roles</span>
        <RouterLink to="/usuarios" :class="{ disabled: !canUse('/usuarios') }" :aria-disabled="!canUse('/usuarios')" @click="handleNav($event, '/usuarios')">Usuarios</RouterLink>
        <RouterLink to="/busqueda-usuarios" :class="{ disabled: !canUse('/busqueda-usuarios') }" :aria-disabled="!canUse('/busqueda-usuarios')" @click="handleNav($event, '/busqueda-usuarios')">Búsqueda de usuarios</RouterLink>
        <RouterLink to="/roles" :class="{ disabled: !canUse('/roles') }" :aria-disabled="!canUse('/roles')" @click="handleNav($event, '/roles')">Roles</RouterLink>
        <RouterLink to="/usuario-roles" :class="{ disabled: !canUse('/usuario-roles') }" :aria-disabled="!canUse('/usuario-roles')" @click="handleNav($event, '/usuario-roles')">Asignación de usuarios</RouterLink>
        <RouterLink to="/medicos" :class="{ disabled: !canUse('/medicos') }" :aria-disabled="!canUse('/medicos')" @click="handleNav($event, '/medicos')">Médicos</RouterLink>
        <RouterLink to="/operadores" :class="{ disabled: !canUse('/operadores') }" :aria-disabled="!canUse('/operadores')" @click="handleNav($event, '/operadores')">Operadores</RouterLink>
        <span class="nav-section">Operación</span>
        <RouterLink to="/pacientes" :class="{ disabled: !canUse('/pacientes') }" :aria-disabled="!canUse('/pacientes')" @click="handleNav($event, '/pacientes')">Pacientes</RouterLink>
        <RouterLink to="/citas" :class="{ disabled: !canUse('/citas') }" :aria-disabled="!canUse('/citas')" @click="handleNav($event, '/citas')">Citas</RouterLink>
        <RouterLink to="/citas/hoy" :class="{ disabled: !canUse('/citas/hoy') }" :aria-disabled="!canUse('/citas/hoy')" @click="handleNav($event, '/citas/hoy')">Citas de hoy</RouterLink>
        <RouterLink to="/contactos-institucionales" :class="{ disabled: !canUse('/contactos-institucionales') }" :aria-disabled="!canUse('/contactos-institucionales')" @click="handleNav($event, '/contactos-institucionales')">Contactos institucionales</RouterLink>
        <RouterLink to="/asignaciones" :class="{ disabled: !canUse('/asignaciones') }" :aria-disabled="!canUse('/asignaciones')" @click="handleNav($event, '/asignaciones')">Asignaciones</RouterLink>
        <RouterLink to="/pantallas-turnos" :class="{ disabled: !canUse('/pantallas-turnos') }" :aria-disabled="!canUse('/pantallas-turnos')" @click="handleNav($event, '/pantallas-turnos')">Pantallas de turnos</RouterLink>
        <RouterLink to="/kioskos" :class="{ disabled: !canUse('/kioskos') }" :aria-disabled="!canUse('/kioskos')" @click="handleNav($event, '/kioskos')">Kioskos</RouterLink>
        <RouterLink to="/turnos-llamados" :class="{ disabled: !canUse('/turnos-llamados') }" :aria-disabled="!canUse('/turnos-llamados')" @click="handleNav($event, '/turnos-llamados')">Turnos llamados</RouterLink>
        <RouterLink to="/reportes" :class="{ disabled: !canUse('/reportes') }" :aria-disabled="!canUse('/reportes')" @click="handleNav($event, '/reportes')">Reportes</RouterLink>
        <RouterLink to="/auditoria" :class="{ disabled: !canUse('/auditoria') }" :aria-disabled="!canUse('/auditoria')" @click="handleNav($event, '/auditoria')">Auditoría</RouterLink>
      </nav>
      <button v-if="getToken()" class="secondary" type="button" @click="logout">Cerrar sesión</button>
    </aside>
    <main class="content">
      <img class="app-header-logo" :src="capitalHeaderLogo" alt="Capital Medical Center" />
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
      <a class="app-footer-link" href="https://astrogatolabs.com.mx/" target="_blank" rel="noopener noreferrer">
        <img class="app-footer-logo" :src="astrogatoLogo" alt="Astrogato Labs" />
      </a>
      <span class="app-footer-clock">
        Zona horaria: {{ footerTimeZone }} · <time :datetime="footerDatetime">{{ footerClock }}</time>
      </span>
    </footer>
  </div>
</template>
