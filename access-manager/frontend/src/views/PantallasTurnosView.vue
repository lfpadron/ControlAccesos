<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import {
  activatePantallaTurnos,
  createPantallaTurnos,
  deactivatePantallaTurnos,
  getPublicDisplayTurnos,
  listComplejos,
  listClustersTurnos,
  listInstituciones,
  listPantallasTurnos,
  listPisos,
  updatePantallaTurnos,
  type ClusterTurnos,
  type Complejo,
  type Institucion,
  type PantallaTurnos,
  type Piso,
  type PublicDisplayTurno,
} from '../api/client';
import { HTML_NAMED_COLORS, type HtmlNamedColorOption } from '../htmlNamedColors';

type NumericInput = number | '';

type PantallaForm = {
  institucion_id: string;
  codigo_dispositivo: string;
  token: string;
  nombre: string;
  descripcion: string;
  complejo_id: string;
  piso_id: string;
  cluster_ids: string[];
  activa: boolean;
  polling_interval_seconds: number;
  color_fondo: string;
  color_texto: string;
  color_turno_nuevo: string;
  color_turno_normal: string;
  font_size_turno_nuevo: NumericInput;
  font_size_turno_normal: NumericInput;
  segundos_resaltado: number;
  segundos_visible: number;
  max_turnos_visibles: number;
};

const pantallas = ref<PantallaTurnos[]>([]);
const instituciones = ref<Institucion[]>([]);
const complejos = ref<Complejo[]>([]);
const pisos = ref<Piso[]>([]);
const clusters = ref<ClusterTurnos[]>([]);
const selected = ref<PantallaTurnos | null>(null);
const turnos = ref<PublicDisplayTurno[]>([]);
const institucionSearch = ref('');
const complejoSearch = ref('');
const pisoSearch = ref('');
const clusterSearch = ref('');
const error = ref('');
const message = ref('');
const loading = ref(false);

const form = reactive<PantallaForm>({
  institucion_id: '',
  codigo_dispositivo: '',
  token: '',
  nombre: '',
  descripcion: '',
  complejo_id: '',
  piso_id: '',
  cluster_ids: [],
  activa: true,
  polling_interval_seconds: 5,
  color_fondo: 'black',
  color_texto: 'white',
  color_turno_nuevo: 'yellow',
  color_turno_normal: 'white',
  font_size_turno_nuevo: 96,
  font_size_turno_normal: 64,
  segundos_resaltado: 25,
  segundos_visible: 300,
  max_turnos_visibles: 10,
});

const colorFamilies = computed(() => {
  const groups: Array<{ family: string; options: HtmlNamedColorOption[] }> = [];
  for (const color of HTML_NAMED_COLORS) {
    let group = groups.find((item) => item.family === color.family);
    if (!group) {
      group = { family: color.family, options: [] };
      groups.push(group);
    }
    group.options.push(color);
  }
  return groups;
});

const filteredComplejos = computed(() => {
  if (!form.institucion_id) return complejos.value;
  return complejos.value.filter((item) => item.institucion_id === form.institucion_id);
});

const filteredPisos = computed(() => {
  if (!form.complejo_id) return pisos.value;
  return pisos.value.filter((item) => item.complejo_id === form.complejo_id);
});

const filteredClusters = computed(() => {
  return clusters.value.filter((item) => {
    if (form.complejo_id && item.complejo_id !== form.complejo_id) return false;
    if (form.piso_id && item.piso_id !== form.piso_id) return false;
    return true;
  });
});

const selectedClusters = computed(() => clusters.value.filter((item) => form.cluster_ids.includes(item.id)));

const previewStyle = computed(() => ({
  backgroundColor: form.color_fondo || 'black',
  color: form.color_texto || 'white',
}));

const displayUrl = computed(() => {
  const codigo = form.codigo_dispositivo.trim();
  if (!codigo) return '';
  const url = new URL(`/display/${encodeURIComponent(codigo)}`, window.location.origin);
  const displayToken = form.token.trim();
  if (displayToken) {
    url.searchParams.set('token', displayToken);
  }
  return url.toString();
});

function institucionLabel(item: Institucion) {
  return item.razon_social ? `${item.nombre} · ${item.razon_social}` : item.nombre;
}

function complejoLabel(item: Complejo) {
  return item.nombre;
}

function pisoLabel(item: Piso) {
  return item.nombre_visible;
}

function clusterLabel(item: ClusterTurnos) {
  return item.nombre;
}

function setAutocompleteLabels() {
  institucionSearch.value = instituciones.value.find((item) => item.id === form.institucion_id)?.nombre ?? '';
  complejoSearch.value = complejos.value.find((item) => item.id === form.complejo_id)?.nombre ?? '';
  pisoSearch.value = pisos.value.find((item) => item.id === form.piso_id)?.nombre_visible ?? '';
}

function matchByLabel<T>(rows: T[], text: string, labeler: (item: T) => string) {
  const normalized = text.trim().toLowerCase();
  return rows.find((item) => labeler(item).toLowerCase() === normalized || labeler(item).split(' · ')[0].toLowerCase() === normalized);
}

function syncInstitution() {
  const match = matchByLabel(instituciones.value, institucionSearch.value, institucionLabel);
  form.institucion_id = match?.id ?? '';
  syncComplex();
}

function syncComplex() {
  const match = matchByLabel(filteredComplejos.value, complejoSearch.value, complejoLabel);
  form.complejo_id = match?.id ?? '';
  if (!filteredPisos.value.some((item) => item.id === form.piso_id)) {
    form.piso_id = '';
    pisoSearch.value = '';
  }
  form.cluster_ids = form.cluster_ids.filter((id) => filteredClusters.value.some((item) => item.id === id));
}

function syncPiso() {
  const match = matchByLabel(filteredPisos.value, pisoSearch.value, pisoLabel);
  form.piso_id = match?.id ?? '';
  form.cluster_ids = form.cluster_ids.filter((id) => filteredClusters.value.some((item) => item.id === id));
}

function addCluster() {
  const match = matchByLabel(filteredClusters.value, clusterSearch.value, clusterLabel);
  if (!match || form.cluster_ids.includes(match.id)) return;
  form.cluster_ids.push(match.id);
  clusterSearch.value = '';
}

function removeCluster(clusterId: string) {
  form.cluster_ids = form.cluster_ids.filter((id) => id !== clusterId);
}

function selectReadonlyValue(event: FocusEvent) {
  (event.target as HTMLInputElement).select();
}

function openDisplayUrl() {
  if (!displayUrl.value) return;
  window.open(displayUrl.value, '_blank', 'noopener,noreferrer');
}

async function loadData() {
  loading.value = true;
  error.value = '';
  try {
    const [pantallasData, institucionesData, complejosData, pisosData, clustersData] = await Promise.all([
      listPantallasTurnos(),
      listInstituciones(),
      listComplejos(),
      listPisos(),
      listClustersTurnos(),
    ]);
    pantallas.value = pantallasData;
    instituciones.value = institucionesData;
    complejos.value = complejosData;
    pisos.value = pisosData;
    clusters.value = clustersData;
    if (!selected.value) resetForm();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar pantallas.';
  } finally {
    loading.value = false;
  }
}

function resetForm() {
  selected.value = null;
  turnos.value = [];
  form.institucion_id = instituciones.value[0]?.id ?? '';
  form.complejo_id = filteredComplejos.value[0]?.id ?? '';
  form.piso_id = filteredPisos.value[0]?.id ?? '';
  form.cluster_ids = [];
  clusterSearch.value = '';
  setAutocompleteLabels();
  form.codigo_dispositivo = '';
  form.token = '';
  form.nombre = '';
  form.descripcion = '';
  form.activa = true;
  form.polling_interval_seconds = 5;
  form.color_fondo = 'black';
  form.color_texto = 'white';
  form.color_turno_nuevo = 'yellow';
  form.color_turno_normal = 'white';
  form.font_size_turno_nuevo = 96;
  form.font_size_turno_normal = 64;
  form.segundos_resaltado = 25;
  form.segundos_visible = 300;
  form.max_turnos_visibles = 10;
}

function setForm(item: PantallaTurnos) {
  selected.value = item;
  const complejo = complejos.value.find((row) => row.id === item.complejo_id);
  form.institucion_id = complejo?.institucion_id ?? '';
  form.complejo_id = item.complejo_id;
  form.piso_id = item.piso_id ?? '';
  form.cluster_ids = [...(item.cluster_ids ?? [])];
  setAutocompleteLabels();
  clusterSearch.value = '';
  form.codigo_dispositivo = item.codigo_dispositivo;
  form.token = '';
  form.nombre = item.nombre ?? '';
  form.descripcion = item.descripcion ?? '';
  form.activa = item.activa;
  form.polling_interval_seconds = item.polling_interval_seconds;
  form.color_fondo = item.color_fondo ?? 'black';
  form.color_texto = item.color_texto ?? 'white';
  form.color_turno_nuevo = item.color_turno_nuevo ?? 'yellow';
  form.color_turno_normal = item.color_turno_normal ?? 'white';
  form.font_size_turno_nuevo = item.font_size_turno_nuevo ?? '';
  form.font_size_turno_normal = item.font_size_turno_normal ?? '';
  form.segundos_resaltado = item.segundos_resaltado;
  form.segundos_visible = item.segundos_visible;
  form.max_turnos_visibles = item.max_turnos_visibles;
  void loadTurnos();
}

function nullable(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function nullableNumber(value: NumericInput) {
  return value === '' ? null : Number(value);
}

function payload() {
  return {
    codigo_dispositivo: form.codigo_dispositivo.trim(),
    nombre: nullable(form.nombre),
    descripcion: nullable(form.descripcion),
    complejo_id: form.complejo_id,
    piso_id: nullable(form.piso_id),
    cluster_espera_id: form.cluster_ids[0] ?? null,
    cluster_ids: form.cluster_ids,
    activa: form.activa,
    polling_interval_seconds: Number(form.polling_interval_seconds),
    color_fondo: nullable(form.color_fondo),
    color_texto: nullable(form.color_texto),
    color_turno_nuevo: nullable(form.color_turno_nuevo),
    color_turno_normal: nullable(form.color_turno_normal),
    font_size_turno_nuevo: nullableNumber(form.font_size_turno_nuevo),
    font_size_turno_normal: nullableNumber(form.font_size_turno_normal),
    segundos_resaltado: Number(form.segundos_resaltado),
    segundos_visible: Number(form.segundos_visible),
    max_turnos_visibles: Number(form.max_turnos_visibles),
    ...(form.token.trim() ? { token: form.token.trim() } : {}),
  };
}

async function submit() {
  loading.value = true;
  error.value = '';
  message.value = '';
  if (!form.cluster_ids.length) {
    error.value = 'Debe asignar al menos un clúster.';
    loading.value = false;
    return;
  }
  try {
    const displayToken = form.token.trim();
    let saved: PantallaTurnos;
    if (selected.value) {
      saved = await updatePantallaTurnos(selected.value.id, payload());
      message.value = 'Pantalla actualizada.';
    } else {
      saved = await createPantallaTurnos(payload());
      message.value = 'Pantalla creada.';
    }
    await loadData();
    setForm(saved);
    form.token = displayToken;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible guardar la pantalla.';
  } finally {
    loading.value = false;
  }
}

async function setActive(item: PantallaTurnos, active: boolean) {
  loading.value = true;
  error.value = '';
  message.value = '';
  try {
    if (active) {
      await activatePantallaTurnos(item.id);
      message.value = 'Pantalla activada.';
    } else {
      await deactivatePantallaTurnos(item.id);
      message.value = 'Pantalla desactivada.';
    }
    await loadData();
    if (selected.value?.id === item.id) resetForm();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cambiar el estado.';
  } finally {
    loading.value = false;
  }
}

async function loadTurnos() {
  turnos.value = [];
  if (!selected.value) return;
  try {
    const response = await getPublicDisplayTurnos(selected.value.codigo_dispositivo, form.token.trim() || undefined);
    turnos.value = response.turnos;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible leer el dispositivo seleccionado.';
  }
}

async function clearDisplayToken() {
  if (!selected.value) return;
  loading.value = true;
  error.value = '';
  message.value = '';
  try {
    const saved = await updatePantallaTurnos(selected.value.id, { token: null });
    message.value = 'Token de pantalla eliminado.';
    await loadData();
    setForm(saved);
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible eliminar el token.';
  } finally {
    loading.value = false;
  }
}

function clustersLabel(item: PantallaTurnos) {
  const names = clusters.value.filter((cluster) => item.cluster_ids?.includes(cluster.id)).map((cluster) => cluster.nombre);
  return names.length ? names.join(', ') : 'Sin clúster';
}

function turnoPreviewText(turno: PublicDisplayTurno) {
  return turno.texto || turno.consultorio;
}

onMounted(loadData);
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Pantallas de turnos</h1>
        <p>Alta, edición y visualización de dispositivos por institución, complejo, piso y clúster.</p>
      </div>
      <button class="secondary" type="button" @click="loadData">Actualizar</button>
    </header>

    <div class="grid catalog-grid">
      <form class="panel form" @submit.prevent="submit">
        <h2>{{ selected ? 'Editar pantalla' : 'Crear pantalla' }}</h2>
        <div class="form-row">
          <label for="institucion-pantalla">Institución</label>
          <input
            id="institucion-pantalla"
            v-model="institucionSearch"
            list="instituciones-pantalla-options"
            required
            @input="syncInstitution"
            @change="syncInstitution"
          />
          <datalist id="instituciones-pantalla-options">
            <option v-for="item in instituciones" :key="item.id" :value="institucionLabel(item)" />
          </datalist>
        </div>

        <div class="form-row">
          <label for="complejo-pantalla">Complejo</label>
          <input
            id="complejo-pantalla"
            v-model="complejoSearch"
            list="complejos-pantalla-options"
            required
            @input="syncComplex"
            @change="syncComplex"
          />
          <datalist id="complejos-pantalla-options">
            <option v-for="item in filteredComplejos" :key="item.id" :value="complejoLabel(item)" />
          </datalist>
        </div>

        <div class="form-row">
          <label for="piso-pantalla">Piso</label>
          <input
            id="piso-pantalla"
            v-model="pisoSearch"
            list="pisos-pantalla-options"
            required
            @input="syncPiso"
            @change="syncPiso"
          />
          <datalist id="pisos-pantalla-options">
            <option v-for="item in filteredPisos" :key="item.id" :value="pisoLabel(item)" />
          </datalist>
        </div>

        <div class="form-row">
          <label for="cluster-pantalla">Clúster</label>
          <div class="autocomplete-add-row">
            <input
              id="cluster-pantalla"
              v-model="clusterSearch"
              list="clusters-pantalla-options"
              @keyup.enter.prevent="addCluster"
            />
            <button class="secondary" type="button" @click="addCluster">Agregar</button>
          </div>
          <datalist id="clusters-pantalla-options">
            <option v-for="item in filteredClusters" :key="item.id" :value="clusterLabel(item)" />
          </datalist>
          <div class="chip-list">
            <button v-for="cluster in selectedClusters" :key="cluster.id" class="chip danger" type="button" @click="removeCluster(cluster.id)">
              × {{ cluster.nombre }}
            </button>
          </div>
        </div>

        <div class="form-grid">
          <div class="form-row">
            <label for="dispositivo">Dispositivo</label>
            <input id="dispositivo" v-model="form.codigo_dispositivo" required maxlength="120" />
          </div>
          <div class="form-row">
            <label for="nombre">Nombre</label>
            <input id="nombre" v-model="form.nombre" maxlength="180" />
          </div>
        </div>
        <div class="form-row">
          <label for="display-url">URL de pantalla</label>
          <div class="autocomplete-add-row">
            <input
              id="display-url"
              :value="displayUrl"
              readonly
              spellcheck="false"
              placeholder="Capture el dispositivo para generar el URL"
              @focus="selectReadonlyValue"
            />
            <button class="secondary" type="button" :disabled="!displayUrl" @click="openDisplayUrl">Abrir</button>
          </div>
        </div>
        <div class="form-row">
          <label for="descripcion">Descripción</label>
          <textarea id="descripcion" v-model="form.descripcion" rows="3" maxlength="1000" />
        </div>
        <div class="form-row">
          <label for="token">Token</label>
          <div class="autocomplete-add-row">
            <input
              id="token"
              v-model="form.token"
              type="password"
              minlength="8"
              maxlength="128"
              autocomplete="new-password"
              placeholder="Opcional"
            />
            <button class="secondary" type="button" :disabled="!selected || loading" @click="clearDisplayToken">Quitar token</button>
          </div>
        </div>
        <div class="form-grid">
          <div class="form-row">
            <label for="polling">Polling</label>
            <input id="polling" v-model.number="form.polling_interval_seconds" type="number" min="2" max="10" required />
          </div>
          <label class="check-row screen-active">
            <input v-model="form.activa" type="checkbox" />
            Activa
          </label>
        </div>

        <h2>Detalle visual</h2>
        <div class="form-grid">
          <div class="form-row">
            <label for="color-fondo">Color de fondo</label>
            <select id="color-fondo" v-model="form.color_fondo">
              <option value="">Sin color</option>
              <optgroup v-for="group in colorFamilies" :key="group.family" :label="group.family">
                <option v-for="color in group.options" :key="`bg-${color.value}`" :value="color.value">
                  {{ color.family }} - {{ color.name }}
                </option>
              </optgroup>
            </select>
          </div>
          <div class="form-row">
            <label for="color-texto">Color de letra</label>
            <select id="color-texto" v-model="form.color_texto">
              <option value="">Sin color</option>
              <optgroup v-for="group in colorFamilies" :key="group.family" :label="group.family">
                <option v-for="color in group.options" :key="`text-${color.value}`" :value="color.value">
                  {{ color.family }} - {{ color.name }}
                </option>
              </optgroup>
            </select>
          </div>
          <div class="form-row">
            <label for="color-nuevo">Color turno nuevo</label>
            <select id="color-nuevo" v-model="form.color_turno_nuevo">
              <option value="">Sin color</option>
              <optgroup v-for="group in colorFamilies" :key="group.family" :label="group.family">
                <option v-for="color in group.options" :key="`new-${color.value}`" :value="color.value">
                  {{ color.family }} - {{ color.name }}
                </option>
              </optgroup>
            </select>
          </div>
          <div class="form-row">
            <label for="color-normal">Color turno normal</label>
            <select id="color-normal" v-model="form.color_turno_normal">
              <option value="">Sin color</option>
              <optgroup v-for="group in colorFamilies" :key="group.family" :label="group.family">
                <option v-for="color in group.options" :key="`normal-${color.value}`" :value="color.value">
                  {{ color.family }} - {{ color.name }}
                </option>
              </optgroup>
            </select>
          </div>
        </div>

        <div class="screen-color-preview" :style="previewStyle">
          <span>{{ form.nombre || 'Pantalla' }}</span>
          <strong>Turno A12</strong>
        </div>

        <div class="form-grid">
          <div class="form-row">
            <label for="size-new">Tamaño turno nuevo</label>
            <input id="size-new" v-model.number="form.font_size_turno_nuevo" type="number" min="24" max="220" />
          </div>
          <div class="form-row">
            <label for="size-normal">Tamaño turno normal</label>
            <input id="size-normal" v-model.number="form.font_size_turno_normal" type="number" min="18" max="160" />
          </div>
          <div class="form-row">
            <label for="segundos-resaltado">Segundos resaltado</label>
            <input id="segundos-resaltado" v-model.number="form.segundos_resaltado" type="number" min="5" max="120" required />
          </div>
          <div class="form-row">
            <label for="segundos-visible">Segundos visible</label>
            <input id="segundos-visible" v-model.number="form.segundos_visible" type="number" min="30" max="3600" required />
          </div>
          <div class="form-row">
            <label for="max-turnos">Máximo de turnos</label>
            <input id="max-turnos" v-model.number="form.max_turnos_visibles" type="number" min="1" max="50" required />
          </div>
        </div>

        <p v-if="message" class="message">{{ message }}</p>
        <p v-if="error" class="error">{{ error }}</p>
        <div class="actions-row">
          <button type="submit" :disabled="loading">{{ loading ? 'Guardando...' : '✓ Guardar' }}</button>
          <button v-if="selected" class="danger solid" type="button" @click="resetForm">× Cancelar</button>
        </div>
      </form>

      <section class="panel table-panel">
        <div class="table-scroll devices-table">
          <table>
            <thead>
              <tr>
                <th>Dispositivo</th>
                <th>Nombre</th>
                <th>Clústers</th>
                <th>Polling</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="pantalla in pantallas"
                :key="pantalla.id"
                class="selectable-row"
                :class="{ selected: selected?.id === pantalla.id }"
                @click="setForm(pantalla)"
              >
                <td>{{ pantalla.codigo_dispositivo }}</td>
                <td>{{ pantalla.nombre || '-' }}</td>
                <td>{{ clustersLabel(pantalla) }}</td>
                <td>{{ pantalla.polling_interval_seconds }} s</td>
                <td>{{ pantalla.activa ? 'Activa' : 'Inactiva' }}</td>
                <td>
                  <div class="inline-actions">
                    <button class="small secondary" type="button" @click.stop="setForm(pantalla)">Editar</button>
                    <button
                      v-if="pantalla.activa"
                      class="small danger"
                      type="button"
                      @click.stop="setActive(pantalla, false)"
                    >
                      Desactivar
                    </button>
                    <button v-else class="small secondary" type="button" @click.stop="setActive(pantalla, true)">
                      Activar
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="!loading && pantallas.length === 0" class="message">No hay pantallas para mostrar.</p>
      </section>
    </div>

    <section class="panel">
      <div class="page-header compact">
        <div>
          <h2>Despliegue actual</h2>
          <p>{{ selected?.codigo_dispositivo || 'Seleccione un dispositivo' }}</p>
        </div>
        <button class="secondary" type="button" :disabled="!selected" @click="loadTurnos">Refrescar</button>
      </div>
      <div v-if="turnos.length" class="turnos-preview">
        <div v-for="turno in turnos" :key="`${turno.turno}-${turno.llamado_en}`" class="turno-preview-item">
          <strong>{{ turno.texto ? 'Texto' : turno.turno }}</strong>
          <span>{{ turnoPreviewText(turno) }}</span>
          <small>{{ turno.estado }}</small>
        </div>
      </div>
      <p v-else class="message">Sin turnos activos para este dispositivo.</p>
    </section>
  </section>
</template>
