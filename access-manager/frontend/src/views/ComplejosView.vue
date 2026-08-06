<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import {
  activateComplejo,
  createComplejo,
  deactivateComplejo,
  listComplejos,
  listInstituciones,
  listZonasHorarias,
  updateComplejo,
  type Complejo,
  type Institucion,
} from '../api/client';
import LocationContextField from '../components/LocationContextField.vue';
import { useLocationContext } from '../composables/useLocationContext';

const complejos = ref<Complejo[]>([]);
const instituciones = ref<Institucion[]>([]);
const selected = ref<Complejo | null>(null);
const nombre = ref('');
const descripcion = ref('');
const direccion = ref('');
const telefono = ref('');
const zonaHoraria = ref('America/Mexico_City');
const activo = ref(true);
const error = ref('');
const message = ref('');
const loading = ref(false);
const zonasHorarias = ref<string[]>([]);

const { clearCampus, locationContext, setCampus, setInstitution } = useLocationContext();

const activeInstitutionId = computed(() => {
  const contextId = locationContext.institucion?.id ?? '';
  return instituciones.value.some((item) => item.id === contextId) ? contextId : '';
});
const selectedInstitution = computed(() => instituciones.value.find((item) => item.id === activeInstitutionId.value) ?? null);
const selectedInstitutionName = computed(() => selectedInstitution.value?.nombre ?? locationContext.institucion?.label ?? '');

const complejosFiltrados = computed(() => {
  return complejos.value
    .filter((item) => item.institucion_id === activeInstitutionId.value)
    .sort((left, right) => left.nombre.localeCompare(right.nombre, 'es', { sensitivity: 'base' }));
});

async function loadData() {
  error.value = '';
  try {
    const [institucionesData, complejosData] = await Promise.all([
      listInstituciones(),
      listComplejos(),
    ]);
    instituciones.value = institucionesData;
    complejos.value = complejosData;
    if (zonasHorarias.value.length === 0) {
      zonasHorarias.value = await listZonasHorarias();
    }
    if (locationContext.institucion && !institucionesData.some((item) => item.id === locationContext.institucion?.id)) {
      setInstitution(null);
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar campus.';
  }
}

function setForm(item?: Complejo | null, syncLocation = true) {
  selected.value = item ?? null;
  nombre.value = item?.nombre ?? '';
  descripcion.value = item?.descripcion ?? '';
  direccion.value = item?.direccion ?? '';
  telefono.value = item?.telefono ?? '';
  zonaHoraria.value = item?.zona_horaria ?? 'America/Mexico_City';
  activo.value = item?.activo ?? true;
  if (!syncLocation) return;
  if (item) {
    const institucion = instituciones.value.find((row) => row.id === item.institucion_id) ?? null;
    setCampus(
      { id: item.id, label: item.nombre },
      institucion ? { id: institucion.id, label: institucion.nombre } : undefined,
    );
  } else {
    clearCampus();
  }
}

async function submit() {
  error.value = '';
  message.value = '';
  loading.value = true;
  try {
    const data = {
      institucion_id: activeInstitutionId.value,
      nombre: nombre.value,
      descripcion: descripcion.value || undefined,
      direccion: direccion.value || undefined,
      telefono: telefono.value || undefined,
      zona_horaria: zonaHoraria.value,
      activo: activo.value,
    };
    let saved: Complejo;
    if (selected.value) {
      saved = await updateComplejo(selected.value.id, data);
      message.value = 'Campus actualizado.';
    } else {
      saved = await createComplejo(data);
      message.value = 'Campus creado.';
    }
    const institucion = instituciones.value.find((row) => row.id === saved.institucion_id) ?? null;
    setCampus(
      { id: saved.id, label: saved.nombre },
      institucion ? { id: institucion.id, label: institucion.nombre } : undefined,
    );
    await loadData();
    setForm(null, false);
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible guardar el campus.';
  } finally {
    loading.value = false;
  }
}

async function setActive(item: Complejo, active: boolean) {
  error.value = '';
  message.value = '';
  loading.value = true;
  try {
    if (active) {
      await activateComplejo(item.id);
      message.value = 'Campus activado.';
    } else {
      await deactivateComplejo(item.id);
      message.value = 'Campus desactivado.';
    }
    await loadData();
    if (selected.value?.id === item.id) setForm(null);
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
        <h1>Campus</h1>
        <p>Torres, edificios o sedes asociadas a una institución.</p>
      </div>
    </header>
    <LocationContextField />

    <div class="grid">
      <form class="panel form compact-form" @submit.prevent="submit">
        <h2>{{ selected ? 'Editar campus' : 'Crear campus' }}</h2>
        <div class="form-row">
          <label for="institucion">Institución</label>
          <input id="institucion" :value="selectedInstitutionName" readonly required />
        </div>
        <div class="form-row">
          <label for="nombre">Nombre</label>
          <input id="nombre" v-model="nombre" required maxlength="180" />
        </div>
        <div class="form-row">
          <label for="descripcion">Descripción</label>
          <textarea id="descripcion" v-model="descripcion" rows="3" />
        </div>
        <div class="form-row">
          <label for="direccion">Dirección</label>
          <textarea id="direccion" v-model="direccion" rows="3" />
        </div>
        <div class="form-row">
          <label for="telefono">Teléfono</label>
          <input id="telefono" v-model="telefono" maxlength="64" />
        </div>
        <div class="form-row">
          <label for="zona">Zona horaria</label>
          <input id="zona" v-model="zonaHoraria" list="zonas-horarias" required maxlength="64" />
          <datalist id="zonas-horarias">
            <option v-for="zona in zonasHorarias" :key="zona" :value="zona" />
          </datalist>
        </div>
        <label class="check-row">
          <input v-model="activo" type="checkbox" />
          Activo
        </label>
        <p v-if="message" class="message">{{ message }}</p>
        <p v-if="error" class="error">{{ error }}</p>
        <div class="actions-row">
          <button type="submit" :disabled="loading || !activeInstitutionId">
            {{ loading ? 'Guardando...' : '✓ Guardar' }}
          </button>
          <button class="danger solid" type="button" @click="setForm(null)">× Cancelar</button>
        </div>
      </form>
      <section class="panel">
        <table>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Zona horaria</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in complejosFiltrados"
              :key="item.id"
              class="selectable-row"
              :class="{ selected: selected?.id === item.id }"
              @click="setForm(item)"
            >
              <td>{{ item.nombre }}</td>
              <td>{{ item.zona_horaria }}</td>
              <td>{{ item.activo ? 'Activo' : 'Inactivo' }}</td>
              <td>
                <div class="inline-actions">
                  <button class="small secondary" type="button" @click.stop="setForm(item)">Editar</button>
                  <button
                    v-if="item.activo"
                    class="small danger"
                    type="button"
                    @click.stop="setActive(item, false)"
                  >
                    Desactivar
                  </button>
                  <button v-else class="small secondary" type="button" @click.stop="setActive(item, true)">
                    Activar
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="complejosFiltrados.length === 0" class="message">No hay campus para mostrar.</p>
      </section>
    </div>
  </section>
</template>
