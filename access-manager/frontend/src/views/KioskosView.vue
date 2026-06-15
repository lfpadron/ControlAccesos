<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import {
  activateKiosko,
  activatePuntoAcceso,
  createKiosko,
  createPuntoAcceso,
  deactivateKiosko,
  deactivatePuntoAcceso,
  listComplejos,
  listInstituciones,
  listKioskos,
  listPisos,
  listPuntosAcceso,
  updateKiosko,
  updatePuntoAcceso,
  type Complejo,
  type Institucion,
  type Kiosko,
  type Piso,
  type PuntoAcceso,
} from '../api/client';
import { HTML_NAMED_COLORS, type HtmlNamedColorOption } from '../htmlNamedColors';

const instituciones = ref<Institucion[]>([]);
const complejos = ref<Complejo[]>([]);
const pisos = ref<Piso[]>([]);
const puntos = ref<PuntoAcceso[]>([]);
const kioskos = ref<Kiosko[]>([]);
const selectedPunto = ref<PuntoAcceso | null>(null);
const selectedKiosko = ref<Kiosko | null>(null);
const error = ref('');
const message = ref('');
const loading = ref(false);

const puntoSearch = reactive({ institucion: '', complejo: '', piso: '' });
const kioskoSearch = reactive({ institucion: '', complejo: '', piso: '', punto: '' });

const puntoForm = reactive({
  institucion_id: '',
  complejo_id: '',
  piso_id: '',
  nombre: '',
  descripcion: '',
  activo: true,
});

const kioskoForm = reactive({
  institucion_id: '',
  codigo_dispositivo: '',
  token: '',
  nombre: '',
  descripcion: '',
  complejo_id: '',
  piso_id: '',
  punto_acceso_id: '',
  activo: true,
  polling_interval_seconds: 5,
  color_fondo: 'white',
  color_texto: 'black',
  color_primario: 'royalblue',
  color_acento: 'seagreen',
});

const colorFields = [
  { key: 'color_fondo', label: 'Color fondo' },
  { key: 'color_texto', label: 'Color texto' },
  { key: 'color_primario', label: 'Color primario' },
  { key: 'color_acento', label: 'Color acento' },
] as const;

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

const puntoComplejos = computed(() =>
  puntoForm.institucion_id ? complejos.value.filter((item) => item.institucion_id === puntoForm.institucion_id) : [],
);
const puntoPisos = computed(() => (puntoForm.complejo_id ? pisos.value.filter((item) => item.complejo_id === puntoForm.complejo_id) : []));
const kioskoComplejos = computed(() =>
  kioskoForm.institucion_id ? complejos.value.filter((item) => item.institucion_id === kioskoForm.institucion_id) : [],
);
const kioskoPisos = computed(() => (kioskoForm.complejo_id ? pisos.value.filter((item) => item.complejo_id === kioskoForm.complejo_id) : []));
const kioskoPuntos = computed(() =>
  puntos.value.filter((item) => item.complejo_id === kioskoForm.complejo_id && item.piso_id === kioskoForm.piso_id),
);

const previewStyle = computed(() => ({
  backgroundColor: kioskoForm.color_fondo || 'white',
  color: kioskoForm.color_texto || 'black',
  borderColor: kioskoForm.color_primario || '#1f6feb',
}));

const kioskoUrl = computed(() => {
  const codigo = kioskoForm.codigo_dispositivo.trim();
  if (!codigo) return '';
  const url = new URL('/kiosk/', window.location.origin);
  url.searchParams.set('device', codigo);
  const token = kioskoForm.token.trim();
  if (token) {
    url.searchParams.set('token', token);
  }
  return url.toString();
});

function institucionLabel(item: Institucion) {
  return item.razon_social ? `${item.nombre} · ${item.razon_social}` : item.nombre;
}

function matchByLabel<T>(rows: T[], text: string, labeler: (item: T) => string) {
  const normalized = text.trim().toLowerCase();
  return rows.find((item) => {
    const label = labeler(item).toLowerCase();
    return label === normalized || label.split(' · ')[0] === normalized;
  });
}

function complejoName(id: string | null | undefined) {
  return complejos.value.find((item) => item.id === id)?.nombre ?? '-';
}

function pisoName(id: string | null | undefined) {
  return pisos.value.find((item) => item.id === id)?.nombre_visible ?? '-';
}

function puntoName(id: string | null | undefined) {
  return puntos.value.find((item) => item.id === id)?.nombre ?? '-';
}

function nullable(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function selectReadonlyValue(event: FocusEvent) {
  (event.target as HTMLInputElement).select();
}

function openKioskoUrl() {
  if (!kioskoUrl.value) return;
  window.open(kioskoUrl.value, '_blank', 'noopener,noreferrer');
}

function setPuntoLabels() {
  puntoSearch.institucion = instituciones.value.find((item) => item.id === puntoForm.institucion_id)?.nombre ?? '';
  puntoSearch.complejo = complejos.value.find((item) => item.id === puntoForm.complejo_id)?.nombre ?? '';
  puntoSearch.piso = pisos.value.find((item) => item.id === puntoForm.piso_id)?.nombre_visible ?? '';
}

function setKioskoLabels() {
  kioskoSearch.institucion = instituciones.value.find((item) => item.id === kioskoForm.institucion_id)?.nombre ?? '';
  kioskoSearch.complejo = complejos.value.find((item) => item.id === kioskoForm.complejo_id)?.nombre ?? '';
  kioskoSearch.piso = pisos.value.find((item) => item.id === kioskoForm.piso_id)?.nombre_visible ?? '';
  kioskoSearch.punto = puntos.value.find((item) => item.id === kioskoForm.punto_acceso_id)?.nombre ?? '';
}

function syncPuntoInstitution() {
  puntoForm.institucion_id = matchByLabel(instituciones.value, puntoSearch.institucion, institucionLabel)?.id ?? '';
  if (!puntoComplejos.value.some((item) => item.id === puntoForm.complejo_id)) {
    puntoForm.complejo_id = '';
    puntoSearch.complejo = '';
    puntoForm.piso_id = '';
    puntoSearch.piso = '';
  }
}

function syncPuntoComplex() {
  puntoForm.complejo_id = matchByLabel(puntoComplejos.value, puntoSearch.complejo, (item) => item.nombre)?.id ?? '';
  if (!puntoPisos.value.some((item) => item.id === puntoForm.piso_id)) {
    puntoForm.piso_id = '';
    puntoSearch.piso = '';
  }
}

function syncPuntoPiso() {
  puntoForm.piso_id = matchByLabel(puntoPisos.value, puntoSearch.piso, (item) => item.nombre_visible)?.id ?? '';
}

function syncKioskoInstitution() {
  kioskoForm.institucion_id = matchByLabel(instituciones.value, kioskoSearch.institucion, institucionLabel)?.id ?? '';
  if (!kioskoComplejos.value.some((item) => item.id === kioskoForm.complejo_id)) {
    kioskoForm.complejo_id = '';
    kioskoSearch.complejo = '';
    kioskoForm.piso_id = '';
    kioskoSearch.piso = '';
    kioskoForm.punto_acceso_id = '';
    kioskoSearch.punto = '';
  }
}

function syncKioskoComplex() {
  kioskoForm.complejo_id = matchByLabel(kioskoComplejos.value, kioskoSearch.complejo, (item) => item.nombre)?.id ?? '';
  if (!kioskoPisos.value.some((item) => item.id === kioskoForm.piso_id)) {
    kioskoForm.piso_id = '';
    kioskoSearch.piso = '';
    kioskoForm.punto_acceso_id = '';
    kioskoSearch.punto = '';
  }
}

function syncKioskoPiso() {
  kioskoForm.piso_id = matchByLabel(kioskoPisos.value, kioskoSearch.piso, (item) => item.nombre_visible)?.id ?? '';
  if (!kioskoPuntos.value.some((item) => item.id === kioskoForm.punto_acceso_id)) {
    kioskoForm.punto_acceso_id = '';
    kioskoSearch.punto = '';
  }
}

function syncKioskoPunto() {
  kioskoForm.punto_acceso_id = matchByLabel(kioskoPuntos.value, kioskoSearch.punto, (item) => item.nombre)?.id ?? '';
}

function resetPuntoForm() {
  selectedPunto.value = null;
  puntoForm.institucion_id = instituciones.value[0]?.id ?? '';
  puntoForm.complejo_id = puntoComplejos.value[0]?.id ?? '';
  puntoForm.piso_id = puntoPisos.value[0]?.id ?? '';
  puntoForm.nombre = '';
  puntoForm.descripcion = '';
  puntoForm.activo = true;
  setPuntoLabels();
}

function resetKioskoForm() {
  selectedKiosko.value = null;
  kioskoForm.institucion_id = instituciones.value[0]?.id ?? '';
  kioskoForm.complejo_id = kioskoComplejos.value[0]?.id ?? '';
  kioskoForm.piso_id = kioskoPisos.value[0]?.id ?? '';
  kioskoForm.punto_acceso_id = kioskoPuntos.value[0]?.id ?? '';
  kioskoForm.codigo_dispositivo = '';
  kioskoForm.token = '';
  kioskoForm.nombre = '';
  kioskoForm.descripcion = '';
  kioskoForm.activo = true;
  kioskoForm.polling_interval_seconds = 5;
  kioskoForm.color_fondo = 'white';
  kioskoForm.color_texto = 'black';
  kioskoForm.color_primario = 'royalblue';
  kioskoForm.color_acento = 'seagreen';
  setKioskoLabels();
}

async function loadData() {
  loading.value = true;
  error.value = '';
  try {
    const [institucionesData, complejosData, pisosData] = await Promise.all([
      listInstituciones(),
      listComplejos(),
      listPisos(),
    ]);
    instituciones.value = institucionesData;
    complejos.value = complejosData;
    pisos.value = pisosData;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar instituciones, complejos y pisos.';
  }

  try {
    const [puntosData, kioskosData] = await Promise.all([listPuntosAcceso(), listKioskos()]);
    puntos.value = puntosData;
    kioskos.value = kioskosData;
  } catch (err) {
    puntos.value = [];
    kioskos.value = [];
    const detail = err instanceof Error ? err.message : 'No fue posible cargar kioskos y puntos de acceso.';
    error.value = error.value ? `${error.value} ${detail}` : `${detail} Verifique que el backend esté actualizado y la migración aplicada.`;
  } finally {
    if (!selectedPunto.value) resetPuntoForm();
    if (!selectedKiosko.value) resetKioskoForm();
    loading.value = false;
  }
}

function setPuntoForm(item: PuntoAcceso) {
  selectedPunto.value = item;
  const complejo = complejos.value.find((row) => row.id === item.complejo_id);
  puntoForm.institucion_id = complejo?.institucion_id ?? '';
  puntoForm.complejo_id = item.complejo_id;
  puntoForm.piso_id = item.piso_id;
  puntoForm.nombre = item.nombre;
  puntoForm.descripcion = item.descripcion ?? '';
  puntoForm.activo = item.activo;
  setPuntoLabels();
}

function setKioskoForm(item: Kiosko) {
  selectedKiosko.value = item;
  const complejo = complejos.value.find((row) => row.id === item.complejo_id);
  kioskoForm.institucion_id = complejo?.institucion_id ?? '';
  kioskoForm.complejo_id = item.complejo_id;
  kioskoForm.piso_id = item.piso_id;
  kioskoForm.punto_acceso_id = item.punto_acceso_id;
  kioskoForm.codigo_dispositivo = item.codigo_dispositivo;
  kioskoForm.token = '';
  kioskoForm.nombre = item.nombre ?? '';
  kioskoForm.descripcion = item.descripcion ?? '';
  kioskoForm.activo = item.activo;
  kioskoForm.polling_interval_seconds = item.polling_interval_seconds;
  kioskoForm.color_fondo = item.color_fondo ?? 'white';
  kioskoForm.color_texto = item.color_texto ?? 'black';
  kioskoForm.color_primario = item.color_primario ?? 'royalblue';
  kioskoForm.color_acento = item.color_acento ?? 'seagreen';
  setKioskoLabels();
}

async function submitPunto() {
  loading.value = true;
  error.value = '';
  message.value = '';
  try {
    const payload = {
      complejo_id: puntoForm.complejo_id,
      piso_id: puntoForm.piso_id,
      nombre: puntoForm.nombre.trim(),
      descripcion: nullable(puntoForm.descripcion),
      activo: puntoForm.activo,
    };
    const saved = selectedPunto.value ? await updatePuntoAcceso(selectedPunto.value.id, payload) : await createPuntoAcceso(payload);
    message.value = selectedPunto.value ? 'Punto de acceso actualizado.' : 'Punto de acceso creado.';
    await loadData();
    setPuntoForm(saved);
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible guardar el punto de acceso.';
  } finally {
    loading.value = false;
  }
}

async function submitKiosko() {
  loading.value = true;
  error.value = '';
  message.value = '';
  if (!selectedKiosko.value && kioskoForm.token.trim().length < 8) {
    error.value = 'El token del kiosko es obligatorio y debe tener al menos 8 caracteres.';
    loading.value = false;
    return;
  }
  try {
    const payload = {
      codigo_dispositivo: kioskoForm.codigo_dispositivo.trim(),
      nombre: nullable(kioskoForm.nombre),
      descripcion: nullable(kioskoForm.descripcion),
      complejo_id: kioskoForm.complejo_id,
      piso_id: kioskoForm.piso_id,
      punto_acceso_id: kioskoForm.punto_acceso_id,
      activo: kioskoForm.activo,
      polling_interval_seconds: Number(kioskoForm.polling_interval_seconds),
      color_fondo: nullable(kioskoForm.color_fondo),
      color_texto: nullable(kioskoForm.color_texto),
      color_primario: nullable(kioskoForm.color_primario),
      color_acento: nullable(kioskoForm.color_acento),
      ...(kioskoForm.token.trim() ? { token: kioskoForm.token.trim() } : {}),
    };
    const saved = selectedKiosko.value ? await updateKiosko(selectedKiosko.value.id, payload) : await createKiosko(payload);
    message.value = selectedKiosko.value ? 'Kiosko actualizado.' : 'Kiosko creado.';
    await loadData();
    setKioskoForm(saved);
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible guardar el kiosko.';
  } finally {
    loading.value = false;
  }
}

async function setPuntoActive(item: PuntoAcceso, active: boolean) {
  loading.value = true;
  error.value = '';
  try {
    await (active ? activatePuntoAcceso(item.id) : deactivatePuntoAcceso(item.id));
    await loadData();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cambiar el estado.';
  } finally {
    loading.value = false;
  }
}

async function setKioskoActive(item: Kiosko, active: boolean) {
  loading.value = true;
  error.value = '';
  try {
    await (active ? activateKiosko(item.id) : deactivateKiosko(item.id));
    await loadData();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cambiar el estado.';
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
        <h1>Kioskos</h1>
        <p>Alta y asignación de kioskos por punto de acceso.</p>
      </div>
      <button class="secondary" type="button" @click="loadData">Actualizar</button>
    </header>

    <p v-if="message" class="message">{{ message }}</p>
    <p v-if="error" class="error">{{ error }}</p>

    <div class="grid catalog-grid">
      <form class="panel form" @submit.prevent="submitPunto">
        <h2>{{ selectedPunto ? 'Editar punto de acceso' : 'Crear punto de acceso' }}</h2>
        <div class="form-row">
          <label for="punto-institucion">Institución</label>
          <input id="punto-institucion" v-model="puntoSearch.institucion" list="punto-instituciones" required @input="syncPuntoInstitution" @change="syncPuntoInstitution" />
          <datalist id="punto-instituciones">
            <option v-for="item in instituciones" :key="item.id" :value="institucionLabel(item)" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="punto-complejo">Complejo</label>
          <input id="punto-complejo" v-model="puntoSearch.complejo" list="punto-complejos" required :disabled="!puntoForm.institucion_id" @input="syncPuntoComplex" @change="syncPuntoComplex" />
          <datalist id="punto-complejos">
            <option v-for="item in puntoComplejos" :key="item.id" :value="item.nombre" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="punto-piso">Piso</label>
          <input id="punto-piso" v-model="puntoSearch.piso" list="punto-pisos" required :disabled="!puntoForm.complejo_id" @input="syncPuntoPiso" @change="syncPuntoPiso" />
          <datalist id="punto-pisos">
            <option v-for="item in puntoPisos" :key="item.id" :value="item.nombre_visible" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="punto-nombre">Nombre</label>
          <input id="punto-nombre" v-model="puntoForm.nombre" required maxlength="180" />
        </div>
        <div class="form-row">
          <label for="punto-descripcion">Descripción</label>
          <textarea id="punto-descripcion" v-model="puntoForm.descripcion" rows="3" />
        </div>
        <label class="check-row">
          <input v-model="puntoForm.activo" type="checkbox" />
          Activo
        </label>
        <div class="actions-row">
          <button type="submit" :disabled="loading">✓ Guardar</button>
          <button class="danger solid" type="button" @click="resetPuntoForm">× Cancelar</button>
        </div>
      </form>

      <section class="panel table-panel">
        <h2>Puntos de acceso</h2>
        <div class="table-scroll devices-table">
          <table>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Complejo</th>
                <th>Piso</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="punto in puntos" :key="punto.id" class="selectable-row" :class="{ selected: selectedPunto?.id === punto.id }" @click="setPuntoForm(punto)">
                <td>{{ punto.nombre }}</td>
                <td>{{ complejoName(punto.complejo_id) }}</td>
                <td>{{ pisoName(punto.piso_id) }}</td>
                <td>{{ punto.activo ? 'Activo' : 'Inactivo' }}</td>
                <td>
                  <div class="inline-actions">
                    <button class="small secondary" type="button" @click.stop="setPuntoForm(punto)">Editar</button>
                    <button v-if="punto.activo" class="small danger" type="button" @click.stop="setPuntoActive(punto, false)">Desactivar</button>
                    <button v-else class="small secondary" type="button" @click.stop="setPuntoActive(punto, true)">Activar</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <div class="grid catalog-grid">
      <form class="panel form" @submit.prevent="submitKiosko">
        <h2>{{ selectedKiosko ? 'Editar kiosko' : 'Crear kiosko' }}</h2>
        <div class="form-row">
          <label for="kiosko-institucion">Institución</label>
          <input id="kiosko-institucion" v-model="kioskoSearch.institucion" list="kiosko-instituciones" required @input="syncKioskoInstitution" @change="syncKioskoInstitution" />
          <datalist id="kiosko-instituciones">
            <option v-for="item in instituciones" :key="item.id" :value="institucionLabel(item)" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="kiosko-complejo">Complejo</label>
          <input id="kiosko-complejo" v-model="kioskoSearch.complejo" list="kiosko-complejos" required :disabled="!kioskoForm.institucion_id" @input="syncKioskoComplex" @change="syncKioskoComplex" />
          <datalist id="kiosko-complejos">
            <option v-for="item in kioskoComplejos" :key="item.id" :value="item.nombre" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="kiosko-piso">Piso</label>
          <input id="kiosko-piso" v-model="kioskoSearch.piso" list="kiosko-pisos" required :disabled="!kioskoForm.complejo_id" @input="syncKioskoPiso" @change="syncKioskoPiso" />
          <datalist id="kiosko-pisos">
            <option v-for="item in kioskoPisos" :key="item.id" :value="item.nombre_visible" />
          </datalist>
        </div>
        <div class="form-row">
          <label for="kiosko-punto">Punto de acceso</label>
          <input id="kiosko-punto" v-model="kioskoSearch.punto" list="kiosko-puntos" required :disabled="!kioskoForm.piso_id" @input="syncKioskoPunto" @change="syncKioskoPunto" />
          <datalist id="kiosko-puntos">
            <option v-for="item in kioskoPuntos" :key="item.id" :value="item.nombre" />
          </datalist>
        </div>

        <div class="form-grid">
          <div class="form-row">
            <label for="kiosko-codigo">Dispositivo</label>
            <input id="kiosko-codigo" v-model="kioskoForm.codigo_dispositivo" required maxlength="120" />
          </div>
          <div class="form-row">
            <label for="kiosko-token">Token</label>
            <input id="kiosko-token" v-model="kioskoForm.token" type="password" minlength="8" maxlength="128" :required="!selectedKiosko" autocomplete="new-password" />
          </div>
        </div>
        <div class="form-row">
          <label for="kiosko-url">URL de kiosko</label>
          <div class="autocomplete-add-row">
            <input
              id="kiosko-url"
              :value="kioskoUrl"
              readonly
              spellcheck="false"
              placeholder="Capture el dispositivo para generar el URL"
              @focus="selectReadonlyValue"
            />
            <button class="secondary" type="button" :disabled="!kioskoUrl" @click="openKioskoUrl">Abrir</button>
          </div>
        </div>
        <div class="form-row">
          <label for="kiosko-nombre">Nombre</label>
          <input id="kiosko-nombre" v-model="kioskoForm.nombre" maxlength="180" />
        </div>
        <div class="form-row">
          <label for="kiosko-descripcion">Descripción</label>
          <textarea id="kiosko-descripcion" v-model="kioskoForm.descripcion" rows="3" />
        </div>
        <div class="form-grid">
          <div class="form-row">
            <label for="kiosko-polling">Polling</label>
            <input id="kiosko-polling" v-model.number="kioskoForm.polling_interval_seconds" type="number" min="2" max="30" required />
          </div>
          <label class="check-row screen-active">
            <input v-model="kioskoForm.activo" type="checkbox" />
            Activo
          </label>
        </div>

        <h2>Colores</h2>
        <div class="form-grid">
          <div class="form-row" v-for="field in colorFields" :key="field.key">
            <label :for="field.key">{{ field.label }}</label>
            <select :id="field.key" v-model="kioskoForm[field.key]">
              <option value="">Sin color</option>
              <optgroup v-for="group in colorFamilies" :key="group.family" :label="group.family">
                <option v-for="color in group.options" :key="`${field.key}-${color.value}`" :value="color.value">
                  {{ color.family }} - {{ color.name }}
                </option>
              </optgroup>
            </select>
          </div>
        </div>
        <div class="screen-color-preview" :style="previewStyle">
          <span>{{ kioskoForm.nombre || 'Kiosko' }}</span>
          <strong>Buscar cita</strong>
        </div>

        <div class="actions-row">
          <button type="submit" :disabled="loading">✓ Guardar</button>
          <button class="danger solid" type="button" @click="resetKioskoForm">× Cancelar</button>
        </div>
      </form>

      <section class="panel table-panel">
        <h2>Kioskos</h2>
        <div class="table-scroll devices-table">
          <table>
            <thead>
              <tr>
                <th>Dispositivo</th>
                <th>Nombre</th>
                <th>Punto</th>
                <th>Polling</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="kiosko in kioskos" :key="kiosko.id" class="selectable-row" :class="{ selected: selectedKiosko?.id === kiosko.id }" @click="setKioskoForm(kiosko)">
                <td>{{ kiosko.codigo_dispositivo }}</td>
                <td>{{ kiosko.nombre || '-' }}</td>
                <td>{{ puntoName(kiosko.punto_acceso_id) }}</td>
                <td>{{ kiosko.polling_interval_seconds }} s</td>
                <td>{{ kiosko.activo ? 'Activo' : 'Inactivo' }}</td>
                <td>
                  <div class="inline-actions">
                    <button class="small secondary" type="button" @click.stop="setKioskoForm(kiosko)">Editar</button>
                    <button v-if="kiosko.activo" class="small danger" type="button" @click.stop="setKioskoActive(kiosko, false)">Desactivar</button>
                    <button v-else class="small secondary" type="button" @click.stop="setKioskoActive(kiosko, true)">Activar</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="!loading && kioskos.length === 0" class="message">No hay kioskos para mostrar.</p>
      </section>
    </div>
  </section>
</template>
