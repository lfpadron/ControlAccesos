<script setup lang="ts">
defineEmits<{
  scan: [];
  search: [];
  create: [];
}>();
</script>

<template>
  <section class="screen">
    <div class="hero">
      <h1>Inicio</h1>
      <p>Acceso móvil preparado para QR, búsqueda y flujos operativos futuros.</p>
    </div>
    <div class="action-list">
      <button class="primary" type="button" @click="$emit('scan')">Escanear QR</button>
      <button class="secondary" type="button" @click="$emit('search')">Buscar paciente</button>
      <button class="secondary" type="button" @click="$emit('create')">Cita espontánea</button>
    </div>
  </section>
</template>
