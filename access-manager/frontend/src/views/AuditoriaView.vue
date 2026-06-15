<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { Auditoria, listAuditoria } from '../api/client';

const rows = ref<Auditoria[]>([]);
const error = ref('');
const loading = ref(false);

async function loadData() {
  loading.value = true;
  error.value = '';
  try {
    rows.value = await listAuditoria();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar la auditoría.';
  } finally {
    loading.value = false;
  }
}

function formatJson(value: Record<string, unknown> | null | undefined) {
  if (!value) {
    return 'Sin datos';
  }
  return JSON.stringify(value, null, 2);
}

onMounted(loadData);
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Auditoría</h1>
        <p>Últimos eventos registrados por cambios administrativos.</p>
      </div>
      <button class="secondary" type="button" @click="loadData">Actualizar</button>
    </header>

    <p v-if="error" class="error">{{ error }}</p>

    <section class="panel">
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Evento</th>
              <th>Entidad</th>
              <th>Usuario</th>
              <th>Después</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in rows" :key="item.id">
              <td>{{ new Date(item.created_at).toLocaleString() }}</td>
              <td>{{ item.evento }}</td>
              <td>{{ item.entidad }}</td>
              <td>{{ item.usuario_id || 'Sistema' }}</td>
              <td><pre>{{ formatJson(item.valor_despues) }}</pre></td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="!loading && rows.length === 0" class="message">No hay eventos de auditoría.</p>
    </section>
  </section>
</template>
