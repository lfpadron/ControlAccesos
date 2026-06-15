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

const complejos = ref<Complejo[]>([]);
const instituciones = ref<Institucion[]>([]);
const selected = ref<Complejo | null>(null);
const institucionId = ref('');
const nombre = ref('');
const descripcion = ref('');
const direccion = ref('');
const telefono = ref('');
const zonaHoraria = ref('America/Mexico_City');
const activo = ref(true);
const filtroInstitucion = ref('');
const institucionFiltradaId = ref('');
const error = ref('');
const message = ref('');
const loading = ref(false);
const zonasHorarias = ref<string[]>([]);

const complejosFiltrados = computed(() => {
  if (!institucionFiltradaId.value) return complejos.value;
  return complejos.value.filter((item) => item.institucion_id === institucionFiltradaId.value);
});

async function loadData() {
  error.value = '';
  try {
    const [institucionesData, complejosData] = await Promise.all([
      listInstituciones(filtroInstitucion.value.trim() || undefined),
      listComplejos(),
    ]);
    instituciones.value = institucionesData;
    complejos.value = complejosData;
    if (zonasHorarias.value.length === 0) {
      zonasHorarias.value = await listZonasHorarias();
    }
    if (!institucionId.value || !institucionesData.some((item) => item.id === institucionId.value)) {
      institucionId.value = institucionesData[0]?.id ?? '';
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar complejos.';
  }
}

function setForm(item?: Complejo | null) {
  selected.value = item ?? null;
  institucionId.value = item?.institucion_id ?? instituciones.value[0]?.id ?? '';
  nombre.value = item?.nombre ?? '';
  descripcion.value = item?.descripcion ?? '';
  direccion.value = item?.direccion ?? '';
  telefono.value = item?.telefono ?? '';
  zonaHoraria.value = item?.zona_horaria ?? 'America/Mexico_City';
  activo.value = item?.activo ?? true;
}

async function submit() {
  error.value = '';
  message.value = '';
  loading.value = true;
  try {
    const data = {
      institucion_id: institucionId.value,
      nombre: nombre.value,
      descripcion: descripcion.value || undefined,
      direccion: direccion.value || undefined,
      telefono: telefono.value || undefined,
      zona_horaria: zonaHoraria.value,
      activo: activo.value,
    };
    if (selected.value) {
      await updateComplejo(selected.value.id, data);
      message.value = 'Complejo actualizado.';
    } else {
      await createComplejo(data);
      message.value = 'Complejo creado.';
    }
    await loadData();
    setForm(null);
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible guardar el complejo.';
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
      message.value = 'Complejo activado.';
    } else {
      await deactivateComplejo(item.id);
      message.value = 'Complejo desactivado.';
    }
    await loadData();
    if (selected.value?.id === item.id) setForm(null);
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cambiar el estado.';
  } finally {
    loading.value = false;
  }
}

async function clearInstitutionFilter() {
  filtroInstitucion.value = '';
  institucionFiltradaId.value = '';
  await loadData();
}

onMounted(loadData);
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Complejos</h1>
        <p>Torres, edificios o sedes asociadas a una institución.</p>
      </div>
    </header>

    <section class="panel">
      <form class="inline-actions" @submit.prevent="loadData">
        <input v-model="filtroInstitucion" class="narrow-input" placeholder="Buscar institución" />
        <button type="submit">Filtrar</button>
        <button class="secondary" type="button" @click="clearInstitutionFilter">Limpiar</button>
        <select v-model="institucionFiltradaId">
          <option value="">Todas las instituciones</option>
          <option v-for="item in instituciones" :key="item.id" :value="item.id">
            {{ item.nombre }}{{ item.razon_social ? ` · ${item.razon_social}` : '' }}
          </option>
        </select>
      </form>
    </section>

    <div class="grid">
      <form class="panel form compact-form" @submit.prevent="submit">
        <h2>{{ selected ? 'Editar complejo' : 'Crear complejo' }}</h2>
        <div class="form-row">
          <label for="institucion">Institución</label>
          <select id="institucion" v-model="institucionId" required>
            <option value="" disabled>Seleccione institución</option>
            <option v-for="item in instituciones" :key="item.id" :value="item.id">
              {{ item.nombre }}{{ item.razon_social ? ` · ${item.razon_social}` : '' }}
            </option>
          </select>
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
          <button type="submit" :disabled="loading || instituciones.length === 0">
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
        <p v-if="complejosFiltrados.length === 0" class="message">No hay complejos para mostrar.</p>
      </section>
    </div>
  </section>
</template>
