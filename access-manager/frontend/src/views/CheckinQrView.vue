<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue';
import { receptionQrCheckin, receptionQrValidate, type CheckinResponse } from '../api/client';

const qrToken = ref('');
const pendingToken = ref('');
const inputRef = ref<HTMLInputElement | null>(null);
const loading = ref(false);
const confirming = ref(false);
const error = ref('');
const result = ref<CheckinResponse | null>(null);
const scans = ref<Array<{ at: string; resultado: string; mensaje: string; folio?: string | null }>>([]);

function focusInput() {
  void nextTick(() => inputRef.value?.focus());
}

function pushScan(response: CheckinResponse) {
  scans.value = [
    {
      at: new Intl.DateTimeFormat('es-MX', { timeStyle: 'medium' }).format(new Date()),
      resultado: response.resultado,
      mensaje: response.mensaje,
      folio: response.folio_turno,
    },
    ...scans.value,
  ].slice(0, 10);
}

async function submitQr() {
  const token = qrToken.value.trim();
  if (!token || loading.value) return;
  loading.value = true;
  error.value = '';
  result.value = null;
  try {
    const response = await receptionQrValidate(token);
    result.value = response;
    pendingToken.value = response.requiere_confirmacion ? token : '';
    pushScan(response);
    if (!response.requiere_confirmacion) {
      qrToken.value = '';
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible validar el QR.';
  } finally {
    loading.value = false;
    if (!result.value?.requiere_confirmacion) {
      focusInput();
    }
  }
}

async function confirmQr() {
  const token = pendingToken.value;
  if (!token || confirming.value) return;
  confirming.value = true;
  error.value = '';
  try {
    const response = await receptionQrCheckin(token);
    result.value = response;
    pendingToken.value = '';
    qrToken.value = '';
    pushScan(response);
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible registrar el check-in.';
  } finally {
    confirming.value = false;
    focusInput();
  }
}

function resetScan() {
  result.value = null;
  pendingToken.value = '';
  qrToken.value = '';
  error.value = '';
  focusInput();
}

function resultClass(response: CheckinResponse | null) {
  if (!response) return '';
  return response.resultado.toLowerCase();
}

onMounted(focusInput);
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Checkin QR</h1>
        <p>Registro de llegada por lectura de QR.</p>
      </div>
      <button class="secondary" type="button" @click="focusInput">Enfocar lector</button>
    </header>

    <section class="panel qr-reader-panel">
      <form class="qr-reader-form" @submit.prevent="submitQr">
        <div class="form-row">
          <label for="checkin-qr-token">QR</label>
          <input
            id="checkin-qr-token"
            ref="inputRef"
            v-model="qrToken"
            autocomplete="off"
            inputmode="none"
            placeholder="Escanee o pegue el código"
          />
        </div>
        <button type="submit" :disabled="loading || !qrToken.trim()">{{ loading ? 'Validando...' : 'Validar' }}</button>
      </form>

      <div v-if="result" class="qr-result" :class="resultClass(result)">
        <strong><span class="qr-result-icon">{{ result.resultado === 'ROJO' ? '✕' : '✓' }}</span>{{ result.mensaje }}</strong>
        <span v-if="result.fecha_label">{{ result.fecha_label }}</span>
        <span v-if="result.torre || result.piso">{{ [result.torre, result.piso].filter(Boolean).join(' · ') }}</span>
        <small v-if="result.folio_turno">Turno {{ result.folio_turno }}</small>
        <div v-if="result.requiere_confirmacion" class="actions-row">
          <button class="success" type="button" :disabled="confirming" @click="confirmQr">{{ confirming ? 'Registrando...' : '✓ Confirmar' }}</button>
          <button class="white-button" type="button" @click="resetScan">Regresar</button>
        </div>
        <div v-else class="actions-row">
          <button class="white-button" type="button" @click="resetScan">Regresar</button>
        </div>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
    </section>

    <section class="panel table-panel">
      <h2>Lecturas recientes</h2>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Hora</th>
              <th>Resultado</th>
              <th>Turno</th>
              <th>Mensaje</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="scan in scans" :key="`${scan.at}-${scan.mensaje}`">
              <td>{{ scan.at }}</td>
              <td><span class="status" :class="scan.resultado === 'VERDE' ? 'ok' : 'muted'">{{ scan.resultado }}</span></td>
              <td>{{ scan.folio || '-' }}</td>
              <td>{{ scan.mensaje }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="scans.length === 0" class="message">Sin lecturas registradas.</p>
    </section>
  </section>
</template>
