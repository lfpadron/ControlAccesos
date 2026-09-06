<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router';
import { canAccessPath } from './accessControl';
import { clearSession, currentSessionUser, isAuthenticated, refreshCurrentSessionUser, setCurrentSessionUser } from './authSession';
import type { Usuario } from './api/client';
import astrogatoLogo from './astrogato-logo-v02.png';
import capitalHeaderLogo from './capital-logo-encabezado.png';
import capitalMenuLogo from './capital-logo-menu.png';
import { useLocationContext } from './composables/useLocationContext';

const router = useRouter();
const route = useRoute();
const fullscreen = computed(() => Boolean(route.meta.fullscreen));
const currentUser = currentSessionUser;
const { clearCampus, clearFloor, clearLocation, clearTower } = useLocationContext();
const showUserBadge = computed(() => Boolean(isAuthenticated.value && currentUser.value && !fullscreen.value && !route.meta.hideUserBadge));
const currentUserDisplayName = computed(() =>
  [currentUser.value?.nombre, currentUser.value?.apellidos].filter(Boolean).join(' ') || currentUser.value?.email || '',
);
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

type NavItem = {
  label: string;
  path: string;
  reset?: () => void;
};

type NavGroup = {
  label: string;
  items: NavItem[];
};

const navGroups: NavGroup[] = [
  {
    label: 'General',
    items: [
      { label: 'Dashboard', path: '/dashboard' },
      { label: 'Perfil', path: '/perfil' },
    ],
  },
  {
    label: 'Instituciones',
    items: [
      { label: 'Instituciones', path: '/instituciones', reset: clearLocation },
      { label: 'Campus', path: '/complejos', reset: clearCampus },
      { label: 'Torres', path: '/torres', reset: clearTower },
      { label: 'Pisos', path: '/pisos', reset: clearFloor },
      { label: 'Salas de espera', path: '/salas-espera' },
      { label: 'Consultorios', path: '/consultorios' },
    ],
  },
  {
    label: 'Personas y roles',
    items: [
      { label: 'Usuarios', path: '/usuarios' },
      { label: 'Búsqueda de usuarios', path: '/busqueda-usuarios' },
      { label: 'Roles', path: '/roles' },
      { label: 'Asignación de usuarios', path: '/usuario-roles' },
      { label: 'Preferencias del médico', path: '/plantilla-turnos' },
    ],
  },
  {
    label: 'Operación',
    items: [
      { label: 'Estado del médico', path: '/estado-medico' },
      { label: 'Pacientes', path: '/pacientes' },
      { label: 'Citas', path: '/citas' },
      { label: 'Citas de hoy', path: '/citas/hoy' },
      { label: 'Recepción', path: '/recepcion' },
      { label: 'Checkin QR', path: '/checkin-qr' },
      { label: 'Contactos institucionales', path: '/contactos-institucionales' },
      { label: 'Clústers', path: '/clusters-turnos' },
      { label: 'Consulta de clústers', path: '/consulta-clusters-consultorios' },
      { label: 'Pantallas de turnos', path: '/pantallas-turnos' },
      { label: 'Consulta de clúster y pantallas', path: '/consulta-clusters-pantallas' },
      { label: 'Kioskos', path: '/kioskos' },
      { label: 'Turnos llamados', path: '/turnos-llamados' },
    ],
  },
  {
    label: 'Reportes',
    items: [
      { label: 'Reportes', path: '/reportes' },
      { label: 'Reportes médicos', path: '/reportes/medicos' },
      { label: 'Reportes recepción', path: '/reportes/recepcion' },
      { label: 'Auditoría', path: '/auditoria' },
    ],
  },
];

const visibleNavGroups = computed(() => {
  const user = currentUser.value;
  if (!user) return [];
  return navGroups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => canAccessPath(user, item.path)),
    }))
    .filter((group) => group.items.length > 0);
});

async function refreshCurrentUser() {
  if (!isAuthenticated.value) {
    setCurrentSessionUser(null);
    return;
  }
  if (fullscreen.value) return;
  try {
    await refreshCurrentSessionUser();
  } catch {
    setCurrentSessionUser(null);
  }
}

function handleCurrentUserUpdated(event: Event) {
  const updatedUser = event instanceof CustomEvent ? (event.detail as Usuario | null | undefined) : undefined;
  if (updatedUser !== undefined) {
    setCurrentSessionUser(updatedUser);
    return;
  }
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
  clearSession();
  router.push('/login');
}

function canUse(path: string) {
  return Boolean(currentUser.value && canAccessPath(currentUser.value, path));
}

function handleNav(event: MouseEvent, item: NavItem) {
  if (!canUse(item.path)) {
    event.preventDefault();
    return;
  }
  item.reset?.();
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
      <p v-if="!currentUser" class="sidebar-welcome">Bienvenido</p>
      <nav v-else-if="visibleNavGroups.length">
        <template v-for="group in visibleNavGroups" :key="group.label">
          <span class="nav-section">{{ group.label }}</span>
          <RouterLink v-for="item in group.items" :key="item.path" :to="item.path" @click="handleNav($event, item)">
            {{ item.label }}
          </RouterLink>
        </template>
      </nav>
      <p v-else class="sidebar-welcome sidebar-welcome-muted">Sin accesos disponibles</p>
      <button v-if="isAuthenticated" class="secondary" type="button" @click="logout">Cerrar sesión</button>
    </aside>
    <main class="content">
      <img class="app-header-logo" :src="capitalHeaderLogo" alt="Capital Medical Center" />
      <div v-if="showUserBadge" class="user-badge-row">
        <RouterLink class="user-badge" to="/perfil">
          <span>Usuario</span>
          <strong>{{ currentUserDisplayName }}</strong>
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
