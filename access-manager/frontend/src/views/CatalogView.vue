<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import {
  activateResource,
  createResource,
  deactivateResource,
  listComplejos,
  listConsultorios,
  listClustersTurnos,
  listInstituciones,
  listMedicos,
  listOperadores,
  listPisos,
  listResource,
  listRoles,
  listTorres,
  listUsuarios,
  updateResource,
} from '../api/client';
import LocationContextField from '../components/LocationContextField.vue';
import { useLocationContext, type LocationSelection } from '../composables/useLocationContext';
import { CatalogColumn, CatalogConfig, CatalogField, catalogs, LookupKey } from '../catalogs';

type Row = Record<string, unknown> & { id: string };
type LookupOption = { id: string; label: string; institucion_id?: string; complejo_id?: string; torre_id?: string; piso_id?: string };
type SelectOption = { value: string; label: string };

const route = useRoute();
const rows = ref<Row[]>([]);
const error = ref('');
const loading = ref(false);
const editingId = ref<string | null>(null);
const form = reactive<Record<string, unknown>>({});
const lookups = reactive<Record<string, LookupOption[]>>({});
const institutionSearch = ref('');
const complexSearch = ref('');

const config = computed<CatalogConfig>(() => catalogs[String(route.meta.catalog)]);
const locationScopedKeys = new Set(['torres', 'pisos', 'salas-espera', 'clusters-turnos', 'consultorios']);
const lockedTowerKeys = new Set(['pisos', 'salas-espera', 'clusters-turnos', 'consultorios']);
const isLocationScoped = computed(() => locationScopedKeys.has(config.value.key));
const isTowerLocked = computed(() => lockedTowerKeys.has(config.value.key));
const {
  clearCampus,
  clearFloor,
  clearLocation,
  clearTower,
  locationContext,
  setCampus,
  setFloor,
  setInstitution,
  setTower,
} = useLocationContext();

const lookupLoaders: Record<LookupKey, () => Promise<LookupOption[]>> = {
  instituciones: async () =>
    (await listInstituciones()).map((item) => ({
      id: item.id,
      label: config.value.institutionScoped
        ? item.nombre
        : item.razon_social
          ? `${item.nombre} · ${item.razon_social}`
          : item.nombre,
    })),
  complejos: async () => (await listComplejos()).map((item) => ({ id: item.id, label: item.nombre, institucion_id: item.institucion_id })),
  torres: async () => (await listTorres()).map((item) => ({ id: item.id, label: item.nombre, complejo_id: item.complejo_id })),
  usuarios: async () => (await listUsuarios()).map((item) => ({ id: item.id, label: `${item.nombre} (${item.email})` })),
  roles: async () => (await listRoles()).map((item) => ({ id: item.id, label: item.codigo })),
  pisos: async () => {
    const [pisos, torres] = await Promise.all([listPisos(), listTorres()]);
    return pisos.map((item) => {
      const torre = torres.find((row) => row.id === item.torre_id);
      return {
        id: item.id,
        label: torre ? `${torre.nombre} · ${item.nombre_visible}` : item.nombre_visible,
        complejo_id: item.complejo_id,
        torre_id: item.torre_id,
      };
    });
  },
  'clusters-turnos': async () =>
    (await listClustersTurnos()).map((item) => ({ id: item.id, label: item.nombre, complejo_id: item.complejo_id, piso_id: item.piso_id })),
  consultorios: async () =>
    (await listConsultorios()).map((item) => ({
      id: item.id,
      label: item.nombre_visible || item.codigo,
      complejo_id: item.complejo_id,
      piso_id: item.piso_id,
    })),
  medicos: async () => (await listMedicos()).map((item) => ({ id: item.id, label: item.nombre_visible || `${item.nombre} ${item.apellidos}` })),
  operadores: async () => (await listOperadores()).map((item) => ({ id: item.id, label: item.usuario_id })),
};

const selectedInstitutionId = computed(() => findOptionByLabel(lookups.instituciones ?? [], institutionSearch.value)?.id ?? '');

const scopedComplejos = computed(() => {
  if (!config.value.institutionScoped) return lookups.complejos ?? [];
  if (!selectedInstitutionId.value) return [];
  return (lookups.complejos ?? []).filter((item) => item.institucion_id === selectedInstitutionId.value);
});

const scopedPisos = computed(() => {
  if (!config.value.institutionScoped) return lookups.pisos ?? [];
  const complejoId = typeof form.complejo_id === 'string' ? form.complejo_id : '';
  const torreId = typeof form.torre_id === 'string' ? form.torre_id : '';
  if (!complejoId) return [];
  if ('torre_id' in form && !torreId) return [];
  return (lookups.pisos ?? []).filter((item) => item.complejo_id === complejoId && (!torreId || item.torre_id === torreId));
});

const scopedTorres = computed(() => {
  if (!config.value.institutionScoped) return lookups.torres ?? [];
  const complejoId = typeof form.complejo_id === 'string' ? form.complejo_id : '';
  if (!complejoId) return [];
  return (lookups.torres ?? []).filter((item) => item.complejo_id === complejoId);
});

const scopedClusters = computed(() => {
  if (!config.value.institutionScoped) return lookups['clusters-turnos'] ?? [];
  const complejoId = typeof form.complejo_id === 'string' ? form.complejo_id : '';
  const pisoId = typeof form.piso_id === 'string' ? form.piso_id : '';
  if (!complejoId || !pisoId) return [];
  return (lookups['clusters-turnos'] ?? []).filter((item) => item.complejo_id === complejoId && item.piso_id === pisoId);
});

const displayedRows = computed(() => rows.value.filter(rowMatchesLocation));

const submitDisabled = computed(() => {
  if (loading.value) return true;
  if (!config.value.institutionScoped) return false;
  if (!selectedInstitutionId.value || !form.complejo_id) return true;
  return config.value.fields.some((field) => {
    if (!field.required) return false;
    if (field.name === 'torre_id' || field.name === 'piso_id') {
      return !form[field.name];
    }
    return false;
  });
});

function normalizeLabel(value: string) {
  return value.trim().toLowerCase();
}

function findOptionByLabel(options: LookupOption[], value: string) {
  const normalized = normalizeLabel(value);
  return options.find((item) => {
    const label = normalizeLabel(item.label);
    const shortLabel = normalizeLabel(item.label.split(' · ')[0]);
    return label === normalized || shortLabel === normalized;
  });
}

function toSelection(option: LookupOption | null | undefined): LocationSelection | null {
  return option ? { id: option.id, label: option.label } : null;
}

function optionById(key: LookupKey, id: unknown) {
  return typeof id === 'string' ? (lookups[key] ?? []).find((item) => item.id === id) ?? null : null;
}

function institutionForCampus(campus: LookupOption | null | undefined) {
  return optionById('instituciones', campus?.institucion_id);
}

function campusForId(id: unknown) {
  return optionById('complejos', id);
}

function towerForId(id: unknown) {
  return optionById('torres', id);
}

function floorForId(id: unknown) {
  return optionById('pisos', id);
}

function currentInstitutionOption() {
  return optionById('instituciones', selectedInstitutionId.value);
}

function currentCampusOption() {
  return campusForId(form.complejo_id);
}

function currentTowerOption() {
  return towerForId(form.torre_id);
}

function currentFloorOption() {
  return floorForId(form.piso_id);
}

const currentTowerLabel = computed(() => currentTowerOption()?.label ?? '');

function setLocationFromForm() {
  if (!isLocationScoped.value) return;
  const institucion = currentInstitutionOption();
  const campus = currentCampusOption();
  const torre = currentTowerOption();
  const piso = currentFloorOption();
  if (!institucion) {
    clearLocation();
  } else if (!campus) {
    setInstitution(toSelection(institucion));
  } else if (!torre) {
    setCampus(toSelection(campus), toSelection(institucion));
  } else if (!piso) {
    setTower(toSelection(torre), toSelection(campus), toSelection(institucion));
  } else {
    setFloor(toSelection(piso), toSelection(torre), toSelection(campus), toSelection(institucion));
  }
}

function setLocationFromRow(row: Row) {
  if (!isLocationScoped.value) return;
  const campus = campusForId(row.complejo_id);
  const institucion = institutionForCampus(campus);
  const rowTorre =
    config.value.key === 'torres'
      ? ({ id: row.id, label: String(row.nombre ?? row.id), complejo_id: row.complejo_id as string } satisfies LookupOption)
      : towerForId(row.torre_id ?? floorForId(row.piso_id)?.torre_id);
  const rowPiso =
    config.value.key === 'pisos'
      ? ({ id: row.id, label: String(row.nombre_visible ?? row.numero ?? row.id), complejo_id: row.complejo_id as string, torre_id: row.torre_id as string } satisfies LookupOption)
      : floorForId(row.piso_id);
  if (!campus || !institucion) return;
  if (rowPiso && rowTorre) {
    setFloor(toSelection(rowPiso), toSelection(rowTorre), toSelection(campus), toSelection(institucion));
  } else if (rowTorre) {
    setTower(toSelection(rowTorre), toSelection(campus), toSelection(institucion));
  } else {
    setCampus(toSelection(campus), toSelection(institucion));
  }
}

function applyLocationContextToForm() {
  if (!config.value.institutionScoped || !isLocationScoped.value) return;
  const institucion = optionById('instituciones', locationContext.institucion?.id);
  const campus = campusForId(locationContext.campus?.id);
  const campusMatchesInstitution = campus && (!institucion || campus.institucion_id === institucion.id);
  institutionSearch.value = institucion?.label ?? '';
  form.complejo_id = campusMatchesInstitution ? campus.id : '';
  complexSearch.value = campusMatchesInstitution ? campus.label : '';

  if ('torre_id' in form) {
    const torre = towerForId(locationContext.torre?.id);
    form.torre_id = torre && torre.complejo_id === form.complejo_id ? torre.id : '';
  }
  if ('piso_id' in form) {
    const piso = floorForId(locationContext.piso?.id);
    const pisoMatchesContext =
      piso &&
      piso.complejo_id === form.complejo_id &&
      (!('torre_id' in form) || !form.torre_id || piso.torre_id === form.torre_id);
    form.piso_id = pisoMatchesContext ? piso.id : '';
    if (pisoMatchesContext && 'torre_id' in form && !form.torre_id) {
      form.torre_id = piso.torre_id ?? '';
    }
  }
}

function rowMatchesLocation(row: Row) {
  if (!isLocationScoped.value) return true;
  const campusId = typeof row.complejo_id === 'string' ? row.complejo_id : '';
  const campus = campusForId(campusId);
  if (locationContext.institucion?.id && campus?.institucion_id !== locationContext.institucion.id) return false;
  if (locationContext.campus?.id && campusId !== locationContext.campus.id) return false;

  if (locationContext.torre?.id) {
    if (config.value.key === 'torres') return row.id === locationContext.torre.id;
    const torreId = typeof row.torre_id === 'string' ? row.torre_id : floorForId(row.piso_id)?.torre_id;
    if (torreId !== locationContext.torre.id) return false;
  }

  if (locationContext.piso?.id && config.value.key !== 'torres') {
    const pisoId = config.value.key === 'pisos' ? row.id : row.piso_id;
    if (pisoId !== locationContext.piso.id) return false;
  }

  return true;
}

function isScopedComplexField(field: CatalogField) {
  return Boolean(config.value.institutionScoped && field.name === 'complejo_id');
}

function isLockedComplexField(field: CatalogField) {
  return Boolean(isLocationScoped.value && isScopedComplexField(field));
}

function isScopedPisoField(field: CatalogField) {
  return Boolean(config.value.institutionScoped && field.name === 'piso_id');
}

function isScopedTorreField(field: CatalogField) {
  return Boolean(config.value.institutionScoped && field.name === 'torre_id');
}

function isLockedTorreField(field: CatalogField) {
  return Boolean(isTowerLocked.value && isScopedTorreField(field));
}

function isScopedClusterField(field: CatalogField) {
  return Boolean(config.value.institutionScoped && field.lookup === 'clusters-turnos');
}

function resetScopedTorre() {
  if ('torre_id' in form) {
    form.torre_id = '';
  }
  resetScopedPiso();
}

function resetScopedPiso() {
  if ('piso_id' in form) {
    form.piso_id = '';
  }
  pruneScopedClusters();
}

function pruneScopedClusters() {
  if (!Array.isArray(form.cluster_ids)) return;
  form.cluster_ids = form.cluster_ids.filter((id) => scopedClusters.value.some((item) => item.id === id));
}

function syncScopedInstitution() {
  if (!config.value.institutionScoped) return;
  if (!selectedInstitutionId.value) {
    form.complejo_id = '';
    complexSearch.value = '';
    resetScopedTorre();
    if (isLocationScoped.value) {
      clearLocation();
    }
    return;
  }
  if (isLocationScoped.value) {
    setInstitution(toSelection(currentInstitutionOption()));
  }
  if (!scopedComplejos.value.some((item) => item.id === form.complejo_id)) {
    form.complejo_id = '';
    complexSearch.value = '';
    resetScopedTorre();
  }
}

function syncScopedComplex() {
  if (!config.value.institutionScoped) return;
  const match = findOptionByLabel(scopedComplejos.value, complexSearch.value);
  form.complejo_id = match?.id ?? '';
  if (isLocationScoped.value) {
    if (match) {
      setCampus(toSelection(match), toSelection(currentInstitutionOption()));
    } else {
      clearCampus();
    }
  }
  if ('torre_id' in form && !scopedTorres.value.some((item) => item.id === form.torre_id)) {
    resetScopedTorre();
  }
  if (!scopedPisos.value.some((item) => item.id === form.piso_id)) {
    resetScopedPiso();
  }
  pruneScopedClusters();
}

function setScopedLabelsFromComplex(complejoId: unknown) {
  if (!config.value.institutionScoped || typeof complejoId !== 'string') return;
  const complejo = (lookups.complejos ?? []).find((item) => item.id === complejoId);
  const institucion = (lookups.instituciones ?? []).find((item) => item.id === complejo?.institucion_id);
  institutionSearch.value = institucion?.label ?? '';
  complexSearch.value = complejo?.label ?? '';
}

function setScopedTorreFromPiso(pisoId: unknown) {
  if (!config.value.institutionScoped || !('torre_id' in form) || typeof pisoId !== 'string') return;
  form.torre_id = (lookups.pisos ?? []).find((item) => item.id === pisoId)?.torre_id ?? '';
}

function resetForm() {
  editingId.value = null;
  for (const key of Object.keys(form)) {
    delete form[key];
  }
  for (const field of config.value.fields) {
    if (field.defaultValue !== undefined) {
      form[field.name] = field.defaultValue;
    } else if (field.type === 'checkbox') {
      form[field.name] = false;
    } else if (field.type === 'multiselect') {
      form[field.name] = [];
    } else {
      form[field.name] = '';
    }
  }
  if (config.value.institutionScoped) {
    institutionSearch.value = '';
    complexSearch.value = '';
    applyLocationContextToForm();
  }
}

function cancelForm() {
  if (isLocationScoped.value && config.value.key === 'torres') {
    clearTower();
  }
  if (isLocationScoped.value && config.value.key === 'pisos') {
    clearFloor();
  }
  resetForm();
}

async function loadLookups() {
  const keys = new Set<LookupKey>();
  if (config.value.institutionScoped) {
    keys.add('instituciones');
    keys.add('complejos');
  }
  for (const field of config.value.fields) {
    if (field.lookup) {
      keys.add(field.lookup);
    }
  }
  for (const column of config.value.columns) {
    if (column.lookup) {
      keys.add(column.lookup);
    }
  }
  await Promise.all(
    [...keys].map(async (key) => {
      lookups[key] = await lookupLoaders[key]();
    }),
  );
}

async function loadRows() {
  rows.value = await listResource<Row>(config.value.resource);
}

async function loadData() {
  loading.value = true;
  error.value = '';
  try {
    await Promise.all([loadLookups(), loadRows()]);
    resetForm();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar el catálogo.';
  } finally {
    loading.value = false;
  }
}

function fieldInputType(field: CatalogField) {
  if (field.type === 'email' || field.type === 'password' || field.type === 'number') {
    return field.type;
  }
  return 'text';
}

function fieldId(field: CatalogField) {
  return `catalog-${config.value.key}-${field.name}`;
}

function fieldName(field: CatalogField) {
  return `catalog_${config.value.key}_${field.name}`;
}

function fieldAutocomplete(field: CatalogField) {
  if (field.type === 'password') {
    return 'new-password';
  }
  if (field.type === 'email') {
    return 'off';
  }
  return undefined;
}

function selectOptions(field: CatalogField): SelectOption[] {
  if (field.options) return field.options;
  return (lookups[field.lookup ?? 'usuarios'] ?? []).map((item) => ({ value: item.id, label: item.label }));
}

function fieldValue(name: string) {
  const value = form[name];
  return value === null || value === undefined ? '' : String(value);
}

function updateField(name: string, event: Event) {
  form[name] = (event.target as HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement).value;
  if (config.value.institutionScoped && name === 'torre_id' && !scopedPisos.value.some((item) => item.id === form.piso_id)) {
    resetScopedPiso();
  }
  if (config.value.institutionScoped && (name === 'piso_id' || name === 'complejo_id' || name === 'torre_id')) {
    pruneScopedClusters();
  }
  if (config.value.institutionScoped && isLocationScoped.value) {
    if (name === 'torre_id' && !form.torre_id) {
      clearTower();
    } else if (name === 'piso_id' && !form.piso_id) {
      clearFloor();
    } else {
      setLocationFromForm();
    }
  }
}

function updateChecked(name: string, event: Event) {
  form[name] = (event.target as HTMLInputElement).checked;
}

function updateMultiselect(name: string, event: Event) {
  form[name] = [...(event.target as HTMLSelectElement).selectedOptions].map((option) => option.value);
}

function normalizePayload() {
  const payload: Record<string, unknown> = {};
  for (const field of config.value.fields) {
    if (field.createOnly && editingId.value) {
      continue;
    }
    if (field.transient) {
      continue;
    }
    let value = form[field.name];
    if (typeof value === 'string' && (field.type === 'email' || field.type === 'password')) {
      value = value.trim();
    }
    if (field.type === 'password' && editingId.value && !value) {
      continue;
    }
    if (field.type === 'number') {
      payload[field.name] = value === '' || value === null || value === undefined ? null : Number(value);
      continue;
    }
    if (field.type === 'checkbox') {
      payload[field.name] = Boolean(value);
      continue;
    }
    if (field.type === 'multiselect') {
      payload[field.name] = Array.isArray(value) ? value : [];
      continue;
    }
    payload[field.name] = value === '' ? null : value;
  }
  return payload;
}

function validatePayload(payload: Record<string, unknown>) {
  for (const field of config.value.fields) {
    if (!field.pattern || !(field.name in payload)) {
      continue;
    }
    const value = payload[field.name];
    if (typeof value === 'string' && value && !new RegExp(field.pattern).test(value)) {
      return field.title ?? `${field.label} no tiene un formato válido.`;
    }
  }
  return '';
}

async function submit() {
  loading.value = true;
  error.value = '';
  if (config.value.institutionScoped) {
    syncScopedInstitution();
    syncScopedComplex();
    if (!selectedInstitutionId.value || !form.complejo_id) {
      error.value = 'Seleccione institución y campus.';
      loading.value = false;
      return;
    }
  }
  const payload = normalizePayload();
  const validationError = validatePayload(payload);
  if (validationError) {
    error.value = validationError;
    loading.value = false;
    return;
  }
  try {
    let saved: Row;
    if (editingId.value) {
      saved = await updateResource<Row>(config.value.resource, editingId.value, payload);
    } else {
      saved = await createResource<Row>(config.value.resource, payload);
    }
    await loadRows();
    setLocationFromRow(saved);
    resetForm();
  } catch (err) {
    error.value = err instanceof Error ? err.message : `No fue posible guardar el ${config.value.entityName}.`;
  } finally {
    loading.value = false;
  }
}

function editRow(row: Row) {
  editingId.value = row.id;
  for (const field of config.value.fields) {
    if (field.createOnly || field.type === 'password') {
      form[field.name] = '';
    } else if (field.type === 'multiselect') {
      form[field.name] = Array.isArray(row[field.name]) ? [...(row[field.name] as unknown[])] : [];
    } else {
      form[field.name] = row[field.name] ?? field.defaultValue ?? (field.type === 'checkbox' ? false : '');
    }
  }
  setScopedLabelsFromComplex(form.complejo_id);
  setScopedTorreFromPiso(form.piso_id);
  setLocationFromRow(row);
}

async function setActive(row: Row, active: boolean) {
  if (!config.value.activeField) {
    return;
  }
  loading.value = true;
  error.value = '';
  try {
    if (active) {
      await activateResource<Row>(config.value.resource, row.id);
    } else {
      await deactivateResource<Row>(config.value.resource, row.id);
    }
    await loadRows();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cambiar el estado.';
  } finally {
    loading.value = false;
  }
}

function staticOptionLabel(options: SelectOption[] | undefined, value: unknown) {
  if (!options || !value) {
    return value ? String(value) : 'Sin asignar';
  }
  if (Array.isArray(value)) {
    return value.length
      ? value.map((item) => options.find((option) => option.value === item)?.label ?? String(item)).join(', ')
      : 'Sin asignar';
  }
  return options.find((item) => item.value === value)?.label ?? String(value);
}

function optionLabel(key: LookupKey | undefined, value: unknown) {
  if (!key || !value) {
    return value ? String(value) : 'Sin asignar';
  }
  if (Array.isArray(value)) {
    return value.length
      ? value.map((item) => lookups[key]?.find((option) => option.id === item)?.label ?? String(item)).join(', ')
      : 'Sin asignar';
  }
  return lookups[key]?.find((item) => item.id === value)?.label ?? String(value);
}

function cellValue(row: Row, column: CatalogColumn) {
  const value = row[column.name];
  if (column.boolean) {
    return value ? 'Activo' : 'Inactivo';
  }
  if (column.options) {
    return staticOptionLabel(column.options, value);
  }
  return optionLabel(column.lookup, value);
}

watch(
  () => route.meta.catalog,
  () => {
    rows.value = [];
    resetForm();
    void loadData();
  },
);

onMounted(loadData);
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>{{ config.title }}</h1>
        <p>{{ config.description }}</p>
      </div>
    </header>
    <LocationContextField v-if="isLocationScoped" />

    <div class="grid catalog-grid">
      <form class="panel form" autocomplete="off" @submit.prevent="submit">
        <h2>{{ editingId ? 'Editar' : 'Crear' }} {{ config.entityName }}</h2>
        <div v-if="config.institutionScoped" class="form-row">
          <label for="catalog-institution">Institución</label>
          <input
            v-if="isLocationScoped"
            id="catalog-institution"
            :value="institutionSearch"
            readonly
            required
          />
          <input
            v-else
            id="catalog-institution"
            v-model="institutionSearch"
            list="catalog-institution-options"
            required
            @input="syncScopedInstitution"
            @change="syncScopedInstitution"
          />
          <datalist id="catalog-institution-options">
            <option v-for="item in lookups.instituciones ?? []" :key="item.id" :value="item.label" />
          </datalist>
        </div>
        <div v-for="field in config.fields" :key="field.name" class="form-row">
          <label v-if="field.type !== 'checkbox'" :for="fieldId(field)">{{ field.label }}</label>
          <template v-if="isScopedComplexField(field)">
            <input
              v-if="isLockedComplexField(field)"
              :id="fieldId(field)"
              :name="fieldName(field)"
              :value="complexSearch"
              :required="field.required"
              readonly
            />
            <input
              v-else
              :id="fieldId(field)"
              v-model="complexSearch"
              list="catalog-complex-options"
              :name="fieldName(field)"
              :required="field.required"
              :disabled="!selectedInstitutionId"
              @input="syncScopedComplex"
              @change="syncScopedComplex"
            />
            <datalist id="catalog-complex-options">
              <option v-for="item in scopedComplejos" :key="item.id" :value="item.label" />
            </datalist>
          </template>
          <template v-else-if="isScopedTorreField(field)">
            <input
              v-if="isLockedTorreField(field)"
              :id="fieldId(field)"
              :name="fieldName(field)"
              :value="currentTowerLabel"
              :required="field.required"
              readonly
            />
            <select
              v-else
              :id="fieldId(field)"
              :name="fieldName(field)"
              :value="fieldValue(field.name)"
              :required="field.required"
              :disabled="!form.complejo_id"
              @change="updateField(field.name, $event)"
            >
              <option value="">{{ field.required ? 'Seleccione torre' : 'Sin asignar' }}</option>
              <option v-for="item in scopedTorres" :key="item.id" :value="item.id">
                {{ item.label }}
              </option>
            </select>
          </template>
          <select
            v-else-if="isScopedPisoField(field)"
            :id="fieldId(field)"
            :name="fieldName(field)"
            :value="fieldValue(field.name)"
            :required="field.required"
            :disabled="!form.complejo_id || ('torre_id' in form && !form.torre_id)"
            @change="updateField(field.name, $event)"
          >
            <option value="">{{ field.required ? 'Seleccione piso' : 'Sin asignar' }}</option>
            <option v-for="item in scopedPisos" :key="item.id" :value="item.id">
              {{ item.label }}
            </option>
          </select>
          <select
            v-else-if="isScopedClusterField(field)"
            :id="fieldId(field)"
            :name="fieldName(field)"
            :value="Array.isArray(form[field.name]) ? form[field.name] : []"
            :required="field.required"
            :disabled="!form.complejo_id || !form.piso_id"
            multiple
            size="5"
            @change="updateMultiselect(field.name, $event)"
          >
            <option v-for="item in scopedClusters" :key="item.id" :value="item.id">
              {{ item.label }}
            </option>
          </select>
          <textarea
            v-else-if="field.type === 'textarea'"
            :id="fieldId(field)"
            :name="fieldName(field)"
            :value="fieldValue(field.name)"
            :required="field.required"
            rows="3"
            @input="updateField(field.name, $event)"
          />
          <select
            v-else-if="field.type === 'select'"
            :id="fieldId(field)"
            :name="fieldName(field)"
            :value="fieldValue(field.name)"
            :required="field.required"
            @change="updateField(field.name, $event)"
          >
            <option v-if="!field.required" value="">Sin asignar</option>
            <option v-for="item in selectOptions(field)" :key="item.value" :value="item.value">
              {{ item.label }}
            </option>
          </select>
          <select
            v-else-if="field.type === 'multiselect'"
            :id="fieldId(field)"
            :name="fieldName(field)"
            :value="Array.isArray(form[field.name]) ? form[field.name] : []"
            :required="field.required"
            multiple
            size="5"
            @change="updateMultiselect(field.name, $event)"
          >
            <option v-for="item in selectOptions(field)" :key="item.value" :value="item.value">
              {{ item.label }}
            </option>
          </select>
          <label v-else-if="field.type === 'checkbox'" class="check-row">
            <input
              :checked="Boolean(form[field.name])"
              :name="fieldName(field)"
              type="checkbox"
              @change="updateChecked(field.name, $event)"
            />
            {{ field.label }}
          </label>
          <input
            v-else
            :id="fieldId(field)"
            :autocomplete="fieldAutocomplete(field)"
            :name="fieldName(field)"
            :value="fieldValue(field.name)"
            :minlength="field.minLength"
            :maxlength="field.maxLength"
            :pattern="field.pattern"
            :required="field.required && !((field.createOnly || field.editOptional) && editingId)"
            :title="field.title"
            :type="fieldInputType(field)"
            @input="updateField(field.name, $event)"
          />
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <div class="actions-row">
          <button type="submit" :disabled="submitDisabled">{{ loading ? 'Guardando...' : '✓ Guardar' }}</button>
          <button v-if="editingId || config.showCancelOnCreate" class="danger solid" type="button" @click="cancelForm">× Cancelar</button>
        </div>
      </form>

      <section class="panel table-panel">
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th v-for="column in config.columns" :key="column.name">{{ column.label }}</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in displayedRows"
                :key="row.id"
                class="selectable-row"
                :class="{ selected: editingId === row.id }"
                @click="editRow(row)"
              >
                <td v-for="column in config.columns" :key="column.name">
                  <span v-if="column.boolean">{{ cellValue(row, column) }}</span>
                  <span v-else>{{ cellValue(row, column) }}</span>
                </td>
                <td>
                  <div class="inline-actions">
                    <button class="small secondary" type="button" @click.stop="editRow(row)">Editar</button>
                    <button
                      v-if="config.activeField && row[config.activeField]"
                      class="small danger"
                      type="button"
                      @click.stop="setActive(row, false)"
                    >
                      Desactivar
                    </button>
                    <button
                      v-else-if="config.activeField"
                      class="small secondary"
                      type="button"
                      @click.stop="setActive(row, true)"
                    >
                      Activar
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="!loading && displayedRows.length === 0" class="message">No hay registros para mostrar.</p>
      </section>
    </div>
  </section>
</template>
