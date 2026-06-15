<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import {
  createContactoInstitucional,
  listComplejos,
  listContactosInstitucionales,
  updateContactoInstitucional,
  type Complejo,
  type ContactoInstitucional,
  type MedioContacto,
} from '../api/client';

const contactos = ref<ContactoInstitucional[]>([]);
const complejos = ref<Complejo[]>([]);
const selected = ref<ContactoInstitucional | null>(null);
const error = ref('');
const message = ref('');

const form = reactive({
  nombre: '',
  tipo_contacto: 'PRIMARIO',
  tipo_contacto_descripcion: '',
  notas: '',
  complejo_ids: [] as string[],
  medios: [
    { tipo: 'CELULAR', valor: '' },
    { tipo: 'CORREO', valor: '' },
    { tipo: 'CELULAR', valor: '' },
    { tipo: 'CORREO', valor: '' },
    { tipo: 'CELULAR', valor: '' },
  ] as MedioContacto[],
});

function setForm(contacto?: ContactoInstitucional | null) {
  selected.value = contacto ?? null;
  form.nombre = contacto?.nombre ?? '';
  form.tipo_contacto = contacto?.tipo_contacto ?? 'PRIMARIO';
  form.tipo_contacto_descripcion = contacto?.tipo_contacto_descripcion ?? '';
  form.notas = contacto?.notas ?? '';
  form.complejo_ids = [...(contacto?.complejo_ids ?? [])];
  const medios = contacto?.medios_contacto ?? [];
  form.medios = Array.from({ length: 5 }, (_, index) => medios[index] ?? { tipo: index % 2 === 0 ? 'CELULAR' : 'CORREO', valor: '' });
}

async function load() {
  error.value = '';
  try {
    const [contactosData, complejosData] = await Promise.all([listContactosInstitucionales(), listComplejos()]);
    contactos.value = contactosData;
    complejos.value = complejosData;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar contactos.';
  }
}

function payload() {
  const medios_contacto = form.medios.filter((item) => item.valor.trim()).map((item) => ({ tipo: item.tipo, valor: item.valor.trim() }));
  return {
    nombre: form.nombre,
    tipo_contacto: form.tipo_contacto,
    tipo_contacto_descripcion: form.tipo_contacto === 'OTRO' ? form.tipo_contacto_descripcion.trim() : null,
    notas: form.notas || null,
    medios_contacto,
    complejo_ids: form.complejo_ids,
  };
}

function tipoContactoLabel(contacto: ContactoInstitucional) {
  if (contacto.tipo_contacto === 'OTRO' && contacto.tipo_contacto_descripcion) {
    return `OTRO - ${contacto.tipo_contacto_descripcion}`;
  }
  return contacto.tipo_contacto;
}

async function submit() {
  error.value = '';
  message.value = '';
  try {
    if (selected.value) {
      await updateContactoInstitucional(selected.value.id, payload());
      message.value = 'Contacto actualizado.';
    } else {
      await createContactoInstitucional(payload());
      message.value = 'Contacto creado.';
    }
    setForm(null);
    await load();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible guardar el contacto.';
  }
}

onMounted(async () => {
  setForm(null);
  await load();
});
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
          <label for="complejos">Complejos asignados</label>
          <select id="complejos" v-model="form.complejo_ids" multiple size="5">
            <option v-for="complejo in complejos" :key="complejo.id" :value="complejo.id">{{ complejo.nombre }}</option>
          </select>
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
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Tipo</th>
                <th>Medios</th>
                <th>Complejos</th>
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
                <td>{{ contacto.medios_contacto.map((item) => item.valor).join(', ') }}</td>
                <td>{{ contacto.complejo_ids.length || 'Todos / sin asignar' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </section>
</template>
