<script setup lang="ts">
import { computed } from 'vue';
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router';
import { clearToken, getToken } from './api/client';

const router = useRouter();
const route = useRoute();
const fullscreen = computed(() => Boolean(route.meta.fullscreen));

function logout() {
  clearToken();
  router.push('/login');
}
</script>

<template>
  <RouterView v-if="fullscreen" />
  <div v-else class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-mark">AM</span>
        <div>
          <strong>Access Manager</strong>
          <small>Control de accesos</small>
        </div>
      </div>
      <nav>
        <span class="nav-section">General</span>
        <RouterLink to="/dashboard">Dashboard</RouterLink>
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
      <RouterView />
    </main>
  </div>
</template>
