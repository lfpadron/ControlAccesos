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
  listUsuarios,
  updateResource,
} from '../api/client';
import { CatalogColumn, CatalogConfig, CatalogField, catalogs, LookupKey } from '../catalogs';

type Row = Record<string, unknown> & { id: string };
type LookupOption = { id: string; label: string; institucion_id?: string; complejo_id?: string; piso_id?: string };
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

const lookupLoaders: Record<LookupKey, () => Promise<LookupOption[]>> = {
  instituciones: async () =>
    (await listInstituciones()).map((item) => ({
      id: item.id,
      label: item.razon_social ? `${item.nombre} · ${item.razon_social}` : item.nombre,
    })),
  complejos: async () => (await listComplejos()).map((item) => ({ id: item.id, label: item.nombre, institucion_id: item.institucion_id })),
  usuarios: async () => (await listUsuarios()).map((item) => ({ id: item.id, label: `${item.nombre} (${item.email})` })),
  roles: async () => (await listRoles()).map((item) => ({ id: item.id, label: item.codigo })),
  pisos: async () => (await listPisos()).map((item) => ({ id: item.id, label: item.nombre_visible, complejo_id: item.complejo_id })),
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
  if (!complejoId) return [];
  return (lookups.pisos ?? []).filter((item) => item.complejo_id === complejoId);
});

const scopedClusters = computed(() => {
  if (!config.value.institutionScoped) return lookups['clusters-turnos'] ?? [];
  const complejoId = typeof form.complejo_id === 'string' ? form.complejo_id : '';
  const pisoId = typeof form.piso_id === 'string' ? form.piso_id : '';
  if (!complejoId || !pisoId) return [];
  return (lookups['clusters-turnos'] ?? []).filter((item) => item.complejo_id === complejoId && item.piso_id === pisoId);
});

const submitDisabled = computed(() => {
  if (loading.value) return true;
  if (!config.value.institutionScoped) return false;
  return !selectedInstitutionId.value || !form.complejo_id;
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

function isScopedComplexField(field: CatalogField) {
  return Boolean(config.value.institutionScoped && field.name === 'complejo_id');
}

function isScopedPisoField(field: CatalogField) {
  return Boolean(config.value.institutionScoped && field.name === 'piso_id');
}

function isScopedClusterField(field: CatalogField) {
  return Boolean(config.value.institutionScoped && field.lookup === 'clusters-turnos');
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
    resetScopedPiso();
    return;
  }
  if (!scopedComplejos.value.some((item) => item.id === form.complejo_id)) {
    form.complejo_id = '';
    complexSearch.value = '';
    resetScopedPiso();
  }
}

function syncScopedComplex() {
  if (!config.value.institutionScoped) return;
  const match = findOptionByLabel(scopedComplejos.value, complexSearch.value);
  form.complejo_id = match?.id ?? '';
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
  }
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

function fieldAutocomplete(field: CatalogField) {
  if (field.type === 'password') {
    return field.createOnly ? 'new-password' : 'off';
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
  if (config.value.institutionScoped && (name === 'piso_id' || name === 'complejo_id')) {
    pruneScopedClusters();
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
    const value = form[field.name];
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

async function submit() {
  loading.value = true;
  error.value = '';
  if (config.value.institutionScoped) {
    syncScopedInstitution();
    syncScopedComplex();
    if (!selectedInstitutionId.value || !form.complejo_id) {
      error.value = 'Seleccione institución y complejo.';
      loading.value = false;
      return;
    }
  }
  try {
    if (editingId.value) {
      await updateResource<Row>(config.value.resource, editingId.value, normalizePayload());
    } else {
      await createResource<Row>(config.value.resource, normalizePayload());
    }
    await loadRows();
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
    if (field.createOnly) {
      form[field.name] = '';
    } else if (field.type === 'multiselect') {
      form[field.name] = Array.isArray(row[field.name]) ? [...(row[field.name] as unknown[])] : [];
    } else {
      form[field.name] = row[field.name] ?? field.defaultValue ?? (field.type === 'checkbox' ? false : '');
    }
  }
  setScopedLabelsFromComplex(form.complejo_id);
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

    <div class="grid catalog-grid">
      <form class="panel form" autocomplete="off" @submit.prevent="submit">
        <h2>{{ editingId ? 'Editar' : 'Crear' }} {{ config.entityName }}</h2>
        <div v-if="config.institutionScoped" class="form-row">
          <label for="catalog-institution">Institución</label>
          <input
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
          <label v-if="field.type !== 'checkbox'" :for="field.name">{{ field.label }}</label>
          <template v-if="isScopedComplexField(field)">
            <input
              :id="field.name"
              v-model="complexSearch"
              list="catalog-complex-options"
              :required="field.required"
              :disabled="!selectedInstitutionId"
              @input="syncScopedComplex"
              @change="syncScopedComplex"
            />
            <datalist id="catalog-complex-options">
              <option v-for="item in scopedComplejos" :key="item.id" :value="item.label" />
            </datalist>
          </template>
          <select
            v-else-if="isScopedPisoField(field)"
            :id="field.name"
            :value="fieldValue(field.name)"
            :required="field.required"
            :disabled="!form.complejo_id"
            @change="updateField(field.name, $event)"
          >
            <option v-if="!field.required" value="">Sin asignar</option>
            <option v-for="item in scopedPisos" :key="item.id" :value="item.id">
              {{ item.label }}
            </option>
          </select>
          <select
            v-else-if="isScopedClusterField(field)"
            :id="field.name"
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
            :id="field.name"
            :value="fieldValue(field.name)"
            :required="field.required"
            rows="3"
            @input="updateField(field.name, $event)"
          />
          <select
            v-else-if="field.type === 'select'"
            :id="field.name"
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
            :id="field.name"
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
            <input :checked="Boolean(form[field.name])" type="checkbox" @change="updateChecked(field.name, $event)" />
            {{ field.label }}
          </label>
          <input
            v-else
            :id="field.name"
            :autocomplete="fieldAutocomplete(field)"
            :value="fieldValue(field.name)"
            :maxlength="field.maxLength"
            :required="field.required && !(field.createOnly && editingId)"
            :type="fieldInputType(field)"
            @input="updateField(field.name, $event)"
          />
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <div class="actions-row">
          <button type="submit" :disabled="submitDisabled">{{ loading ? 'Guardando...' : '✓ Guardar' }}</button>
          <button v-if="editingId || config.showCancelOnCreate" class="danger solid" type="button" @click="resetForm">× Cancelar</button>
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
                v-for="row in rows"
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
        <p v-if="!loading && rows.length === 0" class="message">No hay registros para mostrar.</p>
      </section>
    </div>
  </section>
</template>
