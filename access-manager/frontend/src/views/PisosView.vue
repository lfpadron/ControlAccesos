<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import {
  activateResource,
  deactivateResource,
  listComplejos,
  listInstituciones,
  listPisos,
  listTorres,
  syncTorrePisos,
  updateResource,
  type Complejo,
  type Institucion,
  type Piso,
  type Torre,
} from '../api/client';
import LocationContextField from '../components/LocationContextField.vue';
import { useLocationContext } from '../composables/useLocationContext';

type PisoDraft = {
  codigo: string;
  nombre_visible: string;
  descripcion: string;
  cuenta_con_pantallas: boolean;
};

const instituciones = ref<Institucion[]>([]);
const campus = ref<Complejo[]>([]);
const torres = ref<Torre[]>([]);
const pisos = ref<Piso[]>([]);
const selectedTorreId = ref('');
const drafts = reactive<Record<string, PisoDraft>>({});
const loading = ref(false);
const error = ref('');
const message = ref('');

const { clearTower, locationContext, setTower } = useLocationContext();

const torreOptions = computed(() => {
  const institucionId = locationContext.institucion?.id ?? '';
  const campusId = locationContext.campus?.id ?? '';
  return [...torres.value]
    .filter((item) => {
      if (!item.activo) return false;
      if (campusId) return item.complejo_id === campusId;
      if (!institucionId) return true;
      return campus.value.find((row) => row.id === item.complejo_id)?.institucion_id === institucionId;
    })
    .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es', { sensitivity: 'base' }));
});

const selectedTorre = computed(() => torres.value.find((item) => item.id === selectedTorreId.value) ?? null);
const displayedPisos = computed(() =>
  selectedTorreId.value
    ? pisos.value
        .filter((item) => item.torre_id === selectedTorreId.value)
        .sort((a, b) => a.numero - b.numero)
    : [],
);
const dirtyPisos = computed(() => displayedPisos.value.filter((piso) => isDirty(piso)));

function campusForTorre(torre: Torre | null) {
  return torre ? campus.value.find((item) => item.id === torre.complejo_id) ?? null : null;
}

function institucionForCampus(item: Complejo | null) {
  return item ? instituciones.value.find((row) => row.id === item.institucion_id) ?? null : null;
}

function pisoDraft(piso: Piso): PisoDraft {
  if (!drafts[piso.id]) {
    drafts[piso.id] = {
      codigo: piso.codigo ?? '',
      nombre_visible: piso.nombre_visible,
      descripcion: piso.descripcion ?? '',
      cuenta_con_pantallas: piso.cuenta_con_pantallas,
    };
  }
  return drafts[piso.id];
}

function updateDraft(id: string, field: Extract<keyof PisoDraft, 'codigo' | 'nombre_visible' | 'descripcion'>, event: Event) {
  const target = event.target as HTMLInputElement | HTMLTextAreaElement | null;
  if (!target || !drafts[id]) return;
  drafts[id][field] = target.value;
}

function updateDraftChecked(id: string, event: Event) {
  const target = event.target as HTMLInputElement | null;
  if (!target || !drafts[id]) return;
  drafts[id].cuenta_con_pantallas = target.checked;
}

function syncDrafts() {
  const visibleIds = new Set(displayedPisos.value.map((item) => item.id));
  for (const piso of displayedPisos.value) {
    drafts[piso.id] = {
      codigo: piso.codigo ?? '',
      nombre_visible: piso.nombre_visible,
      descripcion: piso.descripcion ?? '',
      cuenta_con_pantallas: piso.cuenta_con_pantallas,
    };
  }
  for (const id of Object.keys(drafts)) {
    if (!visibleIds.has(id)) {
      delete drafts[id];
    }
  }
}

function isDirty(piso: Piso) {
  const draft = drafts[piso.id];
  if (!draft) return false;
  return (
    draft.codigo !== (piso.codigo ?? '') ||
    draft.nombre_visible !== piso.nombre_visible ||
    draft.descripcion !== (piso.descripcion ?? '') ||
    draft.cuenta_con_pantallas !== piso.cuenta_con_pantallas
  );
}

function setContextFromTorre(torre: Torre) {
  const selectedCampus = campusForTorre(torre);
  const institucion = institucionForCampus(selectedCampus);
  setTower(
    { id: torre.id, label: torre.nombre },
    selectedCampus ? { id: selectedCampus.id, label: selectedCampus.nombre } : null,
    institucion ? { id: institucion.id, label: institucion.nombre } : null,
  );
}

async function refreshPisos() {
  pisos.value = await listPisos();
  syncDrafts();
}

async function synchronizeSelectedTower(showMessage = false) {
  if (!selectedTorreId.value) return;
  const synced = await syncTorrePisos(selectedTorreId.value);
  pisos.value = [...pisos.value.filter((item) => item.torre_id !== selectedTorreId.value), ...synced];
  syncDrafts();
  if (showMessage) {
    message.value = 'Pisos sincronizados.';
  }
}

async function synchronizeFromButton() {
  error.value = '';
  message.value = '';
  loading.value = true;
  try {
    await synchronizeSelectedTower(true);
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible sincronizar pisos de la torre.';
  } finally {
    loading.value = false;
  }
}

async function handleTowerChange() {
  error.value = '';
  message.value = '';
  const torre = selectedTorre.value;
  if (!torre) {
    clearTower();
    syncDrafts();
    return;
  }
  setContextFromTorre(torre);
  loading.value = true;
  try {
    await synchronizeSelectedTower();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible sincronizar pisos de la torre.';
  } finally {
    loading.value = false;
  }
}

function validateDraft(piso: Piso) {
  const draft = pisoDraft(piso);
  const nombre = draft.nombre_visible.trim();
  const descripcion = draft.descripcion.trim();
  if (!nombre) return `Capture nombre visible para el piso ${piso.numero}.`;
  if (nombre.length > 20) return `Nombre visible del piso ${piso.numero} no debe exceder 20 caracteres.`;
  if (descripcion.length > 200) return `Descripción del piso ${piso.numero} no debe exceder 200 caracteres.`;
  return '';
}

async function saveChanges() {
  error.value = '';
  message.value = '';
  const rows = dirtyPisos.value;
  for (const piso of rows) {
    const validationError = validateDraft(piso);
    if (validationError) {
      error.value = validationError;
      return;
    }
  }
  loading.value = true;
  try {
    for (const piso of rows) {
      const draft = pisoDraft(piso);
      await updateResource<Piso>('pisos', piso.id, {
        codigo: draft.codigo.trim() || null,
        nombre_visible: draft.nombre_visible.trim(),
        descripcion: draft.descripcion.trim() || null,
        cuenta_con_pantallas: draft.cuenta_con_pantallas,
      });
    }
    await refreshPisos();
    message.value = rows.length === 1 ? 'Piso actualizado.' : 'Pisos actualizados.';
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible guardar pisos.';
  } finally {
    loading.value = false;
  }
}

async function setPisoActive(piso: Piso, active: boolean) {
  error.value = '';
  message.value = '';
  loading.value = true;
  try {
    if (active) {
      await activateResource<Piso>('pisos', piso.id);
    } else {
      await deactivateResource<Piso>('pisos', piso.id);
    }
    await refreshPisos();
    message.value = active ? 'Piso activado.' : 'Piso desactivado.';
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cambiar el estado del piso.';
  } finally {
    loading.value = false;
  }
}

async function loadData() {
  loading.value = true;
  error.value = '';
  try {
    const [institucionesData, campusData, torresData, pisosData] = await Promise.all([
      listInstituciones(),
      listComplejos(),
      listTorres(),
      listPisos(),
    ]);
    instituciones.value = institucionesData;
    campus.value = campusData;
    torres.value = torresData;
    pisos.value = pisosData;
    selectedTorreId.value = torreOptions.value.some((item) => item.id === locationContext.torre?.id)
      ? locationContext.torre?.id ?? ''
      : '';
    if (selectedTorreId.value) {
      await synchronizeSelectedTower();
    } else {
      syncDrafts();
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar pisos.';
  } finally {
    loading.value = false;
  }
}

onMounted(loadData);
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Pisos</h1>
        <p>Edición de pisos generados automáticamente por torre.</p>
      </div>
    </header>
    <LocationContextField />

    <section class="panel">
      <div class="form-grid">
        <div class="form-row">
          <label for="pisos-torre">Torre</label>
          <select id="pisos-torre" v-model="selectedTorreId" @change="handleTowerChange">
            <option value="">Seleccione torre</option>
            <option v-for="torre in torreOptions" :key="torre.id" :value="torre.id">
              {{ torre.nombre }}
            </option>
          </select>
        </div>
      </div>
      <div class="actions-row">
        <button type="button" :disabled="loading || !selectedTorreId || dirtyPisos.length === 0" @click="saveChanges">
          {{ loading ? 'Guardando...' : 'Guardar cambios' }}
        </button>
        <button class="secondary" type="button" :disabled="loading || !selectedTorreId" @click="synchronizeFromButton">Sincronizar pisos</button>
      </div>
      <p v-if="selectedTorre" class="message">Número de pisos definido en torre: {{ selectedTorre.numero_pisos }}</p>
      <p v-if="message" class="message">{{ message }}</p>
      <p v-if="error" class="error">{{ error }}</p>
    </section>

    <section v-if="selectedTorreId" class="panel table-panel">
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Número de piso</th>
              <th>Código de piso</th>
              <th>Nombre visible</th>
              <th>Descripción</th>
              <th>Cuenta con pantallas</th>
              <th>Activar/desactivar</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="piso in displayedPisos" :key="piso.id">
              <td>{{ piso.numero }}</td>
              <td>
                <input :value="pisoDraft(piso).codigo" maxlength="40" @input="updateDraft(piso.id, 'codigo', $event)" />
              </td>
              <td>
                <input :value="pisoDraft(piso).nombre_visible" required maxlength="20" @input="updateDraft(piso.id, 'nombre_visible', $event)" />
              </td>
              <td>
                <textarea :value="pisoDraft(piso).descripcion" maxlength="200" rows="2" @input="updateDraft(piso.id, 'descripcion', $event)"></textarea>
              </td>
              <td>
                <label class="check-row">
                  <input :checked="pisoDraft(piso).cuenta_con_pantallas" type="checkbox" @change="updateDraftChecked(piso.id, $event)" />
                  Cierto
                </label>
              </td>
              <td>
                <button v-if="piso.activo" class="small danger" type="button" :disabled="loading" @click="setPisoActive(piso, false)">Desactivar</button>
                <button v-else class="small secondary" type="button" :disabled="loading" @click="setPisoActive(piso, true)">Activar</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="!loading && displayedPisos.length === 0" class="message">No hay pisos para mostrar.</p>
    </section>
    <section v-else class="panel">
      <p class="message">Seleccione una torre para consultar y editar sus pisos.</p>
    </section>
  </section>
</template>
