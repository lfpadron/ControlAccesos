<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import {
  getApiHealth,
  listAuditoria,
  listComplejos,
  listConsultorios,
  listInstituciones,
  listMedicos,
  listOperadores,
  listRoles,
  listUsuarios,
} from '../api/client';

const metrics = ref([
  { label: 'Instituciones', value: '...' },
  { label: 'Complejos', value: '...' },
  { label: 'Usuarios', value: '...' },
  { label: 'Roles', value: '...' },
  { label: 'Consultorios', value: '...' },
  { label: 'Médicos', value: '...' },
  { label: 'Operadores', value: '...' },
  { label: 'Eventos de auditoría', value: '...' },
]);
const apiStatus = ref('Validando...');
const loading = ref(true);

onMounted(async () => {
  const [
    health,
    institucionesData,
    complejosData,
    usuariosData,
    rolesData,
    consultoriosData,
    medicosData,
    operadoresData,
    auditoriaData,
  ] = await Promise.all([
    getApiHealth(),
    listInstituciones(),
    listComplejos(),
    listUsuarios(),
    listRoles(),
    listConsultorios(),
    listMedicos(),
    listOperadores(),
    listAuditoria(),
  ]);
  apiStatus.value = health.status.toUpperCase();
  metrics.value = [
    { label: 'Instituciones', value: String(institucionesData.length) },
    { label: 'Complejos', value: String(complejosData.length) },
    { label: 'Usuarios', value: String(usuariosData.length) },
    { label: 'Roles', value: String(rolesData.length) },
    { label: 'Consultorios', value: String(consultoriosData.length) },
    { label: 'Médicos', value: String(medicosData.length) },
    { label: 'Operadores', value: String(operadoresData.length) },
    { label: 'Eventos de auditoría', value: String(auditoriaData.length) },
  ];
  loading.value = false;
});
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Dashboard</h1>
        <p>Vista inicial de operación multiinstitución.</p>
      </div>
      <div class="actions-row">
        <RouterLink class="button-link secondary" to="/turnos-llamados">Turnos llamados</RouterLink>
        <span class="status ok">API {{ apiStatus }}</span>
      </div>
    </header>
    <div class="grid">
      <article v-for="metric in metrics" :key="metric.label" class="panel">
        <p class="message">{{ metric.label }}</p>
        <h2>{{ loading ? '...' : metric.value }}</h2>
      </article>
    </div>
  </section>
</template>
