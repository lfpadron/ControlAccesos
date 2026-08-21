<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import {
  createContactoInstitucional,
  listContactosInstitucionales,
  listContactosInstitucionalesCatalogos,
  updateContactoInstitucional,
  type Complejo,
  type ContactoInstitucional,
  type Institucion,
  type MedioContacto,
  type Torre,
} from '../api/client';

type ContactoTipo = ContactoInstitucional['tipo_contacto'];

const contactos = ref<ContactoInstitucional[]>([]);
const instituciones = ref<Institucion[]>([]);
const institucionesBusqueda = ref<Institucion[]>([]);
const complejos = ref<Complejo[]>([]);
const torres = ref<Torre[]>([]);
const selected = ref<ContactoInstitucional | null>(null);
const error = ref('');
const message = ref('');
const loading = ref(false);
const formInstitutionSearch = ref('');
const campusAssignSearch = ref('');
const torreAssignSearch = ref('');

const filters = reactive({
  institucion_id: '',
  complejo_id: '',
  torre_id: '',
  q: '',
});

const filterSearch = reactive({
  institucion: '',
  campus: '',
  torre: '',
});

const form = reactive({
  institucion_id: '',
  nombre: '',
  tipo_contacto: 'PRIMARIO' as ContactoTipo,
  tipo_contacto_descripcion: '',
  notas: '',
  complejo_ids: [] as string[],
  torre_ids: [] as string[],
  medios: [
    { tipo: 'CELULAR', valor: '' },
    { tipo: 'CORREO', valor: '' },
    { tipo: 'CELULAR', valor: '' },
    { tipo: 'CORREO', valor: '' },
    { tipo: 'CELULAR', valor: '' },
  ] as MedioContacto[],
});

const institutionOptions = computed(() => sortByLabel(instituciones.value, institucionLabel));
const formInstitutionOptions = computed(() => sortByLabel(instituciones.value, formInstitucionLabel));
const searchInstitutionOptions = computed(() => sortByLabel(institucionesBusqueda.value, formInstitucionLabel));
const canSearchAllInstitutions = computed(() => searchInstitutionOptions.value.length === 0);
const canSearchContactos = computed(() => canSearchAllInstitutions.value || Boolean(filters.institucion_id));

const filteredComplejos = computed(() => {
  if (!filters.institucion_id) return [];
  return sortByLabel(
    complejos.value.filter((item) => item.institucion_id === filters.institucion_id),
    campusLabel,
  );
});

const filteredTorres = computed(() => {
  if (!filters.complejo_id) return [];
  return sortByLabel(
    torres.value.filter((item) => item.complejo_id === filters.complejo_id),
    torreLabel,
  );
});

const assignmentComplejos = computed(() => {
  if (!form.institucion_id) return [];
  return sortByLabel(
    complejos.value.filter((item) => item.institucion_id === form.institucion_id),
    campusLabel,
  );
});

const assignmentTorres = computed(() => {
  if (!form.institucion_id) return [];
  const campusIds = new Set(
    complejos.value.filter((item) => item.institucion_id === form.institucion_id).map((item) => item.id),
  );
  return sortByLabel(
    torres.value.filter((item) => campusIds.has(item.complejo_id)),
    torreFullLabel,
  );
});

const selectedComplejos = computed(() =>
  sortByLabel(
    form.complejo_ids.map((id) => complejos.value.find((item) => item.id === id)).filter((item): item is Complejo => Boolean(item)),
    campusLabel,
  ),
);

const selectedTorres = computed(() =>
  sortByLabel(
    form.torre_ids.map((id) => torres.value.find((item) => item.id === id)).filter((item): item is Torre => Boolean(item)),
    torreFullLabel,
  ),
);

function sortByLabel<T>(rows: T[], labeler: (item: T) => string) {
  return [...rows].sort((left, right) => labeler(left).localeCompare(labeler(right), 'es', { numeric: true, sensitivity: 'base' }));
}

function normalizeAutocompleteText(text: string) {
  return text
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase();
}

function matchByLabel<T>(rows: T[], text: string, labeler: (item: T) => string) {
  const normalized = normalizeAutocompleteText(text);
  return rows.find((item) => {
    const label = normalizeAutocompleteText(labeler(item));
    return label === normalized || normalizeAutocompleteText(label.split(' · ')[0] ?? '') === normalized;
  });
}

function institucionLabel(item: Institucion) {
  return item.razon_social ? `${item.nombre} · ${item.razon_social}` : item.nombre;
}

function formInstitucionLabel(item: Institucion) {
  return item.nombre;
}

function campusLabel(item: Complejo) {
  return item.nombre;
}

function torreLabel(item: Torre) {
  return item.nombre;
}

function campusForTorre(torre: Torre) {
  return complejos.value.find((item) => item.id === torre.complejo_id) ?? null;
}

function torreFullLabel(item: Torre) {
  const campus = campusForTorre(item);
  return campus ? `${item.nombre} · ${campus.nombre}` : item.nombre;
}

function defaultFormInstitution() {
  return formInstitutionOptions.value.length === 1 ? formInstitutionOptions.value[0] : null;
}

function clearFormLocations() {
  form.complejo_ids = [];
  form.torre_ids = [];
  campusAssignSearch.value = '';
  torreAssignSearch.value = '';
}

function syncFormInstitution() {
  const previousId = form.institucion_id;
  const match = matchByLabel(formInstitutionOptions.value, formInstitutionSearch.value, formInstitucionLabel);
  form.institucion_id = match?.id ?? '';
  if (match) {
    formInstitutionSearch.value = formInstitucionLabel(match);
  }
  if (previousId !== form.institucion_id) {
    clearFormLocations();
  }
}

function setForm(contacto?: ContactoInstitucional | null) {
  selected.value = contacto ?? null;
  const defaultInstitution = defaultFormInstitution();
  const institutionId = contacto?.institucion_id ?? defaultInstitution?.id ?? '';
  const institution = institutionOptions.value.find((item) => item.id === institutionId) ?? null;
  form.institucion_id = institutionId;
  formInstitutionSearch.value = institution ? formInstitucionLabel(institution) : '';
  form.nombre = contacto?.nombre ?? '';
  form.tipo_contacto = contacto?.tipo_contacto ?? 'PRIMARIO';
  form.tipo_contacto_descripcion = contacto?.tipo_contacto_descripcion ?? '';
  form.notas = contacto?.notas ?? '';
  form.complejo_ids = [...(contacto?.complejo_ids ?? [])];
  form.torre_ids = [...(contacto?.torre_ids ?? [])];
  campusAssignSearch.value = '';
  torreAssignSearch.value = '';
  const medios = contacto?.medios_contacto ?? [];
  form.medios = Array.from({ length: 5 }, (_, index) => medios[index] ?? { tipo: index % 2 === 0 ? 'CELULAR' : 'CORREO', valor: '' });
}

function setFilterInstitution(item: Institucion | null, loadResults = true) {
  const previousId = filters.institucion_id;
  filters.institucion_id = item?.id ?? '';
  filterSearch.institucion = item ? formInstitucionLabel(item) : canSearchAllInstitutions.value ? 'Todas las instituciones' : '';
  filters.complejo_id = '';
  filters.torre_id = '';
  filterSearch.campus = '';
  filterSearch.torre = '';
  if (!canSearchContactos.value) {
    contactos.value = [];
    return;
  }
  if (loadResults && (previousId !== filters.institucion_id || canSearchAllInstitutions.value)) {
    void loadContactos();
  }
}

function syncFilterInstitution() {
  setFilterInstitution(matchByLabel(searchInstitutionOptions.value, filterSearch.institucion, formInstitucionLabel) ?? null);
}

function syncFilterCampus() {
  const previousId = filters.complejo_id;
  const match = matchByLabel(filteredComplejos.value, filterSearch.campus, campusLabel);
  filters.complejo_id = match?.id ?? '';
  filterSearch.campus = match ? campusLabel(match) : filterSearch.campus;
  filters.torre_id = '';
  filterSearch.torre = '';
  if (previousId !== filters.complejo_id) {
    void loadContactos();
  }
}

function syncFilterTorre() {
  const previousId = filters.torre_id;
  const match = matchByLabel(filteredTorres.value, filterSearch.torre, torreLabel);
  filters.torre_id = match?.id ?? '';
  filterSearch.torre = match ? torreLabel(match) : filterSearch.torre;
  if (previousId !== filters.torre_id) {
    void loadContactos();
  }
}

function applyDefaultInstitution(loadResults = true) {
  if (searchInstitutionOptions.value.length === 1) {
    setFilterInstitution(searchInstitutionOptions.value[0], loadResults);
  } else {
    setFilterInstitution(null, loadResults);
  }
}

async function load() {
  error.value = '';
  loading.value = true;
  try {
    const catalogos = await listContactosInstitucionalesCatalogos();
    instituciones.value = catalogos.instituciones;
    institucionesBusqueda.value = catalogos.instituciones_busqueda ?? catalogos.instituciones;
    complejos.value = catalogos.complejos;
    torres.value = catalogos.torres;
    setForm(null);
    applyDefaultInstitution(false);
    if (canSearchContactos.value) {
      await loadContactos();
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar contactos.';
  } finally {
    loading.value = false;
  }
}

async function loadContactos() {
  if (!canSearchContactos.value) {
    contactos.value = [];
    return;
  }
  error.value = '';
  loading.value = true;
  try {
    contactos.value = await listContactosInstitucionales({
      institucion_id: filters.institucion_id || undefined,
      complejo_id: filters.complejo_id,
      torre_id: filters.torre_id,
      q: filters.q.trim() || undefined,
    });
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible buscar contactos.';
  } finally {
    loading.value = false;
  }
}

function clearFilters() {
  filters.q = '';
  applyDefaultInstitution();
}

function addComplejo() {
  if (!form.institucion_id) return;
  const match = matchByLabel(assignmentComplejos.value, campusAssignSearch.value, campusLabel);
  if (!match || form.complejo_ids.includes(match.id)) return;
  form.complejo_ids.push(match.id);
  campusAssignSearch.value = '';
}

function removeComplejo(complejoId: string) {
  form.complejo_ids = form.complejo_ids.filter((id) => id !== complejoId);
}

function addTorre() {
  if (!form.institucion_id) return;
  const match = matchByLabel(assignmentTorres.value, torreAssignSearch.value, torreFullLabel);
  if (!match || form.torre_ids.includes(match.id)) return;
  form.torre_ids.push(match.id);
  torreAssignSearch.value = '';
}

function removeTorre(torreId: string) {
  form.torre_ids = form.torre_ids.filter((id) => id !== torreId);
}

function payload() {
  const medios_contacto = form.medios.filter((item) => item.valor.trim()).map((item) => ({ tipo: item.tipo, valor: item.valor.trim() }));
  return {
    institucion_id: form.institucion_id,
    nombre: form.nombre.trim(),
    tipo_contacto: form.tipo_contacto,
    tipo_contacto_descripcion: form.tipo_contacto === 'OTRO' ? form.tipo_contacto_descripcion.trim() : null,
    notas: form.notas.trim() || null,
    medios_contacto,
    complejo_ids: form.complejo_ids,
    torre_ids: form.torre_ids,
  };
}

function tipoContactoLabel(contacto: ContactoInstitucional) {
  if (contacto.tipo_contacto === 'OTRO' && contacto.tipo_contacto_descripcion) {
    return `OTRO - ${contacto.tipo_contacto_descripcion}`;
  }
  return contacto.tipo_contacto;
}

function contactoCorreos(contacto: ContactoInstitucional) {
  return contacto.medios_contacto.filter((item) => item.tipo === 'CORREO').map((item) => item.valor).join(', ') || '-';
}

function contactoCampusLabel(contacto: ContactoInstitucional) {
  if (!contacto.complejo_ids.length && !contacto.torre_ids.length) return 'Toda la institución';
  const names = contacto.complejo_ids
    .map((id) => complejos.value.find((item) => item.id === id))
    .filter((item): item is Complejo => Boolean(item))
    .map(campusLabel);
  return names.length ? names.join(', ') : '-';
}

function contactoTorresLabel(contacto: ContactoInstitucional) {
  if (!contacto.torre_ids.length) return '-';
  return contacto.torre_ids
    .map((id) => torres.value.find((item) => item.id === id))
    .filter((item): item is Torre => Boolean(item))
    .map(torreFullLabel)
    .join(', ');
}

async function submit() {
  error.value = '';
  message.value = '';
  if (!form.institucion_id) {
    error.value = 'Seleccione una institución asignada.';
    return;
  }
  try {
    if (selected.value) {
      await updateContactoInstitucional(selected.value.id, payload());
      message.value = 'Contacto actualizado.';
    } else {
      await createContactoInstitucional(payload());
      message.value = 'Contacto creado.';
    }
    setForm(null);
    await loadContactos();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible guardar el contacto.';
  }
}

onMounted(load);
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1>Contactos institucionales</h1>
        <p>Responsables a contactar en casos excepcionales.</p>
      </div>
    </header>

    <div class="grid catalog-grid">
      <form class="panel form" @submit.prevent="submit">
        <h2>{{ selected ? 'Editar contacto' : 'Crear contacto' }}</h2>
        <div class="form-row">
          <label for="contacto-institucion-asignada">Institución asignada</label>
          <input
            id="contacto-institucion-asignada"
            v-model="formInstitutionSearch"
            list="contacto-institucion-asignada-options"
            required
            placeholder="Selecciona una institución"
            @input="syncFormInstitution"
            @change="syncFormInstitution"
          />
          <datalist id="contacto-institucion-asignada-options">
            <option v-for="institucion in formInstitutionOptions" :key="institucion.id" :value="formInstitucionLabel(institucion)" />
          </datalist>
        </div>

        <div class="form-row">
          <label for="contacto-campus-asignar">Campus asignados</label>
          <div class="autocomplete-add-row">
            <input
              id="contacto-campus-asignar"
              v-model="campusAssignSearch"
              list="contacto-campus-asignar-options"
              :disabled="!form.institucion_id"
              placeholder="Selecciona una institución"
              @keyup.enter.prevent="addComplejo"
            />
            <button class="secondary" type="button" :disabled="!form.institucion_id" @click="addComplejo">Agregar</button>
          </div>
          <datalist id="contacto-campus-asignar-options">
            <option v-for="complejo in assignmentComplejos" :key="complejo.id" :value="campusLabel(complejo)" />
          </datalist>
          <div class="chip-list">
            <button
              v-for="complejo in selectedComplejos"
              :key="complejo.id"
              class="chip danger"
              type="button"
              @click="removeComplejo(complejo.id)"
            >
              × {{ campusLabel(complejo) }}
            </button>
          </div>
        </div>

        <div class="form-row">
          <label for="contacto-torre-asignar">Torres asignadas</label>
          <div class="autocomplete-add-row">
            <input
              id="contacto-torre-asignar"
              v-model="torreAssignSearch"
              list="contacto-torre-asignar-options"
              :disabled="!form.institucion_id"
              placeholder="Selecciona una institución"
              @keyup.enter.prevent="addTorre"
            />
            <button class="secondary" type="button" :disabled="!form.institucion_id" @click="addTorre">Agregar</button>
          </div>
          <datalist id="contacto-torre-asignar-options">
            <option v-for="torre in assignmentTorres" :key="torre.id" :value="torreFullLabel(torre)" />
          </datalist>
          <div class="chip-list">
            <button v-for="torre in selectedTorres" :key="torre.id" class="chip danger" type="button" @click="removeTorre(torre.id)">
              × {{ torreFullLabel(torre) }}
            </button>
          </div>
        </div>

        <div class="form-row">
          <label for="nombre">Nombre</label>
          <input id="nombre" v-model="form.nombre" required maxlength="180" />
        </div>
        <div class="form-row">
          <label for="tipo">Tipo de contacto</label>
          <select id="tipo" v-model="form.tipo_contacto">
            <option value="PRIMARIO">Primario</option>
            <option value="SECUNDARIO">Secundario</option>
            <option value="SOLO_EMERGENCIAS">Solo emergencias</option>
            <option value="OTRO">Otro</option>
          </select>
        </div>
        <div v-if="form.tipo_contacto === 'OTRO'" class="form-row">
          <label for="tipo-descripcion">Describir tipo</label>
          <input id="tipo-descripcion" v-model="form.tipo_contacto_descripcion" required maxlength="50" />
        </div>
        <div class="form-row">
          <label>Medios de contacto</label>
          <div v-for="(medio, index) in form.medios" :key="index" class="contact-medium">
            <select v-model="medio.tipo">
              <option value="CELULAR">Celular</option>
              <option value="CORREO">Correo</option>
            </select>
            <input v-model="medio.valor" :placeholder="index < 2 ? 'Obligatorio' : 'Opcional'" maxlength="180" />
          </div>
        </div>

        <div class="form-row">
          <label for="notas">Notas</label>
          <textarea id="notas" v-model="form.notas" rows="4" />
        </div>
        <div class="actions-row">
          <button type="submit">✓ Guardar</button>
          <button v-if="selected" class="danger solid" type="button" @click="setForm(null)">× Cancelar</button>
        </div>
        <p v-if="message" class="message">{{ message }}</p>
        <p v-if="error" class="error">{{ error }}</p>
      </form>

      <section class="panel table-panel">
        <form class="form" @submit.prevent="loadContactos">
          <h2>Búsqueda</h2>
          <div class="form-grid">
            <div class="form-row">
              <label for="contacto-institucion">Institución</label>
              <input
                id="contacto-institucion"
                v-model="filterSearch.institucion"
                list="contacto-institucion-options"
                :disabled="canSearchAllInstitutions"
                @input="syncFilterInstitution"
                @change="syncFilterInstitution"
              />
              <datalist id="contacto-institucion-options">
                <option v-for="institucion in searchInstitutionOptions" :key="institucion.id" :value="formInstitucionLabel(institucion)" />
              </datalist>
            </div>
            <div class="form-row">
              <label for="contacto-campus">Campus</label>
              <input
                id="contacto-campus"
                v-model="filterSearch.campus"
                list="contacto-campus-options"
                :disabled="!filters.institucion_id"
                @input="syncFilterCampus"
                @change="syncFilterCampus"
              />
              <datalist id="contacto-campus-options">
                <option v-for="complejo in filteredComplejos" :key="complejo.id" :value="campusLabel(complejo)" />
              </datalist>
            </div>
            <div class="form-row">
              <label for="contacto-torre">Torre</label>
              <input
                id="contacto-torre"
                v-model="filterSearch.torre"
                list="contacto-torre-options"
                :disabled="!filters.complejo_id"
                @input="syncFilterTorre"
                @change="syncFilterTorre"
              />
              <datalist id="contacto-torre-options">
                <option v-for="torre in filteredTorres" :key="torre.id" :value="torreLabel(torre)" />
              </datalist>
            </div>
          </div>
          <div class="form-row">
            <label for="contacto-q">Nombre o correo electrónico</label>
            <div class="autocomplete-add-row">
              <input
                id="contacto-q"
                v-model="filters.q"
                :disabled="!canSearchContactos"
                :placeholder="canSearchAllInstitutions ? 'Buscar en todas las instituciones' : 'Selecciona una institución para buscar'"
              />
              <button type="submit" :disabled="!canSearchContactos || loading">{{ loading ? 'Buscando...' : 'Buscar' }}</button>
            </div>
          </div>
          <div class="actions-row">
            <button class="secondary" type="button" @click="clearFilters">Limpiar</button>
          </div>
        </form>

        <p v-if="!canSearchContactos" class="message">Selecciona una institución para buscar contactos.</p>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Tipo</th>
                <th>Correos</th>
                <th>Campus</th>
                <th>Torres</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="contacto in contactos"
                :key="contacto.id"
                class="selectable-row"
                :class="{ selected: selected?.id === contacto.id }"
                @click="setForm(contacto)"
              >
                <td>{{ contacto.nombre }}</td>
                <td>{{ tipoContactoLabel(contacto) }}</td>
                <td>{{ contactoCorreos(contacto) }}</td>
                <td>{{ contactoCampusLabel(contacto) }}</td>
                <td>{{ contactoTorresLabel(contacto) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="canSearchContactos && !loading && contactos.length === 0" class="message">No hay contactos para mostrar.</p>
      </section>
    </div>
  </section>
</template>
