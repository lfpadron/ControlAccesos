<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import MobileHomeView from './views/MobileHomeView.vue';
import ScanQrView from './views/ScanQrView.vue';
import SearchPatientView from './views/SearchPatientView.vue';
import CreateWalkinView from './views/CreateWalkinView.vue';

type Screen = 'home' | 'scan' | 'search' | 'create';

const screen = ref<Screen>('home');
const apiStatus = ref('Verificando API...');
const version = import.meta.env.VITE_APP_VERSION ?? 'v0.2.0';

const title = computed(() => {
  if (screen.value === 'scan') return 'Escanear QR';
  if (screen.value === 'search') return 'Buscar paciente';
  if (screen.value === 'create') return 'Cita espontánea';
  return 'Inicio';
});

onMounted(async () => {
  try {
    const response = await fetch('/api/health');
    const data = await response.json();
    apiStatus.value = data.status === 'ok' ? 'API OK' : 'API no disponible';
  } catch {
    apiStatus.value = 'API no disponible';
  }
});
</script>

<template>
  <main class="mobile-shell">
    <header>
      <strong>Access Manager</strong>
      <div class="header-meta">
        <span>{{ title }}</span>
        <small>{{ apiStatus }} - {{ version }}</small>
      </div>
    </header>
    <MobileHomeView v-if="screen === 'home'" @scan="screen = 'scan'" @search="screen = 'search'" @create="screen = 'create'" />
    <ScanQrView v-else-if="screen === 'scan'" @back="screen = 'home'" />
    <SearchPatientView v-else-if="screen === 'search'" @back="screen = 'home'" />
    <CreateWalkinView v-else @back="screen = 'home'" />
  </main>
</template>
