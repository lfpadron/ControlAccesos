<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import {
  activatePaciente,
  createPaciente,
  deactivatePaciente,
  getCurrentUser,
  listAccessibleMedicos,
  listPacientes,
  markPacienteForDeletion,
  searchPacientes,
  updatePaciente,
  type Medico,
  type Paciente,
  type Usuario,
} from '../api/client';

const pacientes = ref<Paciente[]>([]);
const medicos = ref<Medico[]>([]);
const currentUser = ref<Usuario | null>(null);
const selected = ref<Paciente | null>(null);
const loading = ref(false);
const error = ref('');
const message = ref('');
const query = ref('');
const medicoId = ref('');
const confirmPreferredOnly = ref(false);
const birthYearInput = ref<HTMLInputElement | null>(null);
const birthMonthInput = ref<HTMLInputElement | null>(null);
const birthDayInput = ref<HTMLInputElement | null>(null);

type PhoneType = 'FIJO' | 'CELULAR';
type ConfirmationMethodOption = { value: string; label: string };

const form = reactive({
  nombre: '',
  nombre_preferido: '',
  apellido_paterno: '',
  apellido_materno: '',
  telefono_1: '',
  tipo_telefono_1: 'FIJO' as PhoneType,
  celular: '',
  tipo_telefono_2: 'CELULAR' as PhoneType,
  correo_electronico: '',
  metodo_confirmacion: '',
  fecha_nacimiento: '',
});

const birthDate = reactive({
  year: '',
  month: '',
  day: '',
});

const isPreferredOnly = computed(
  () =>
    Boolean(form.nombre_preferido.trim()) &&
    !form.nombre.trim() &&
    !form.apellido_paterno.trim() &&
    !form.apellido_materno.trim(),
);
const canEditPatient = computed(() => Boolean(medicoId.value));

function validEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

function lastFourDigits(value: string) {
  const digits = value.replace(/\D/g, '');
  return (digits || value.trim()).slice(-4);
}

function buildConfirmationMethodOptions(patient: {
  telefono_1?: string | null;
  tipo_telefono_1?: PhoneType | null;
  celular?: string | null;
  tipo_telefono_2?: PhoneType | null;
  correo_electronico?: string | null;
}): ConfirmationMethodOption[] {
  const phones = [
    { position: 1, value: patient.telefono_1?.trim() ?? '', type: patient.tipo_telefono_1 ?? 'FIJO' },
    { position: 2, value: patient.celular?.trim() ?? '', type: patient.tipo_telefono_2 ?? 'CELULAR' },
  ].filter((phone) => phone.value);
  const fixedPhones = phones.filter((phone) => phone.type === 'FIJO');
  const mobilePhones = phones.filter((phone) => phone.type === 'CELULAR');
  const labelFor = (label: string, phone: (typeof phones)[number], matches: typeof phones) =>
    matches.length > 1 ? `${label} (${lastFourDigits(phone.value)})` : label;
  const options: ConfirmationMethodOption[] = [];

  for (const phone of fixedPhones) {
    options.push({ value: `LLAMAR_FIJO_${phone.position}`, label: labelFor('Llamar por teléfono fijo', phone, fixedPhones) });
  }
  for (const phone of mobilePhones) {
    options.push({ value: `LLAMAR_CELULAR_${phone.position}`, label: labelFor('Llamar por celular', phone, mobilePhones) });
  }
  for (const phone of mobilePhones) {
    options.push({ value: `WHATSAPP_${phone.position}`, label: labelFor('WhatsApp', phone, mobilePhones) });
  }
  for (const phone of mobilePhones) {
    options.push({ value: `TELEGRAM_${phone.position}`, label: labelFor('Telegram', phone, mobilePhones) });
  }
  if (patient.correo_electronico && validEmail(patient.correo_electronico)) {
    options.push({ value: 'CORREO', label: 'Correo' });
  }
  return options;
}

const confirmationMethodOptions = computed(() => buildConfirmationMethodOptions(form));
const sortedPacientes = computed(() =>
  [...pacientes.value].sort((left, right) => {
    const leftName = patientSortName(left);
    const rightName = patientSortName(right);
    if (!leftName && rightName) return 1;
    if (leftName && !rightName) return -1;
    const byName = leftName.localeCompare(rightName, 'es', { numeric: true, sensitivity: 'base' });
    if (byName !== 0) return byName;
    return left.folio_paciente.localeCompare(right.folio_paciente, 'es', { numeric: true, sensitivity: 'base' });
  }),
);

watch(confirmationMethodOptions, (options) => {
  if (form.metodo_confirmacion && !options.some((option) => option.value === form.metodo_confirmacion)) {
    form.metodo_confirmacion = '';
  }
});

function patientDisplayName(paciente: Paciente) {
  const apellidos = [paciente.apellido_paterno, paciente.apellido_materno].filter(Boolean).join(' ');
  const nombre = paciente.nombre?.trim() ?? '';
  if (apellidos && nombre) return `${apellidos}, ${nombre}`;
  return apellidos || nombre || '-';
}

function patientSortName(paciente: Paciente) {
  return [paciente.apellido_paterno, paciente.apellido_materno, paciente.nombre].filter(Boolean).join(' ').trim();
}

function medicoLabel(medico: Medico) {
  return [medico.apellidos, medico.nombre].filter(Boolean).join(' ');
}

function setMedicoSelection(id: string) {
  medicoId.value = id;
}

function defaultMedicoId() {
  const ownMedico = medicos.value.find((medico) => medico.usuario_id && medico.usuario_id === currentUser.value?.id);
  return ownMedico?.id ?? (medicos.value.length === 1 ? medicos.value[0].id : '');
}

function setBirthDateParts(value?: string | null) {
  const [year = '', month = '', day = ''] = value?.split('-') ?? [];
  birthDate.year = year;
  birthDate.month = month;
  birthDate.day = day;
  form.fecha_nacimiento = value ?? '';
}

function syncBirthDate() {
  if (!birthDate.year && !birthDate.month && !birthDate.day) {
    form.fecha_nacimiento = '';
    return;
  }
  if (birthDate.year.length !== 4 || birthDate.month.length !== 2 || birthDate.day.length !== 2) {
    form.fecha_nacimiento = '';
    return;
  }
  const isoDate = `${birthDate.year}-${birthDate.month}-${birthDate.day}`;
  const date = new Date(`${isoDate}T00:00:00`);
  const valid =
    !Number.isNaN(date.getTime()) &&
    date.getFullYear() === Number(birthDate.year) &&
    date.getMonth() + 1 === Number(birthDate.month) &&
    date.getDate() === Number(birthDate.day);
  form.fecha_nacimiento = valid ? isoDate : '';
}

function handleBirthDateInput(part: keyof typeof birthDate, maxLength: number, next?: 'month' | 'day') {
  birthDate[part] = birthDate[part].replace(/\D/g, '').slice(0, maxLength);
  syncBirthDate();
  if (birthDate[part].length === maxLength) {
    if (next === 'month') birthMonthInput.value?.focus();
    if (next === 'day') birthDayInput.value?.focus();
  }
}

function hasIncompleteBirthDate() {
  return Boolean(birthDate.year || birthDate.month || birthDate.day) && !form.fecha_nacimiento;
}

function trimOrNull(value: string) {
  const text = value.trim();
  return text || null;
}

function setForm(paciente?: Paciente | null) {
  selected.value = paciente ?? null;
  form.nombre = paciente?.nombre ?? '';
  form.nombre_preferido = paciente?.nombre_preferido ?? '';
  form.apellido_paterno = paciente?.apellido_paterno ?? '';
  form.apellido_materno = paciente?.apellido_materno ?? '';
  form.telefono_1 = paciente?.telefono_1 ?? '';
  form.tipo_telefono_1 = paciente?.tipo_telefono_1 ?? 'FIJO';
  form.celular = paciente?.celular ?? '';
  form.tipo_telefono_2 = paciente?.tipo_telefono_2 ?? 'CELULAR';
  form.correo_electronico = paciente?.correo_electronico ?? '';
  form.metodo_confirmacion = paciente?.metodo_confirmacion ?? '';
  setBirthDateParts(paciente?.fecha_nacimiento ?? '');
  confirmPreferredOnly.value = false;
}

async function load() {
  error.value = '';
  if (!medicoId.value) {
    pacientes.value = [];
    loading.value = false;
    return;
  }
  loading.value = true;
  try {
    pacientes.value = await listPacientes({ medico_id: medicoId.value });
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar pacientes.';
  } finally {
    loading.value = false;
  }
}

async function search() {
  error.value = '';
  if (!medicoId.value) {
    pacientes.value = [];
    return;
  }
  if (!query.value.trim()) {
    await load();
    return;
  }
  loading.value = true;
  try {
    pacientes.value = await searchPacientes(query.value.trim(), medicoId.value);
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible buscar pacientes.';
  } finally {
    loading.value = false;
  }
}

async function submit(preferredOnlyConfirmed = false) {
  error.value = '';
  message.value = '';
  if (!medicoId.value) {
    error.value = 'Selecciona un médico antes de crear o editar pacientes.';
    return;
  }
  if (hasIncompleteBirthDate()) {
    error.value = 'Completa la fecha de nacimiento con año, mes y día válidos.';
    return;
  }
  if (!form.nombre_preferido.trim() && (!form.nombre.trim() || !form.apellido_paterno.trim())) {
    error.value = 'Captura nombre preferido o nombre y apellido paterno.';
    return;
  }
  if (!form.telefono_1.trim() || !form.celular.trim()) {
    error.value = 'Teléfono 1 y Teléfono 2 son obligatorios.';
    return;
  }
  if (form.correo_electronico.trim() && !validEmail(form.correo_electronico)) {
    error.value = 'Captura un correo electrónico válido.';
    return;
  }
  if (
    form.metodo_confirmacion &&
    !confirmationMethodOptions.value.some((option) => option.value === form.metodo_confirmacion)
  ) {
    error.value = 'Selecciona un método de envío y confirmación disponible.';
    return;
  }
  if (isPreferredOnly.value && !preferredOnlyConfirmed) {
    confirmPreferredOnly.value = true;
    return;
  }
  confirmPreferredOnly.value = false;
  try {
    const payload = {
      nombre: trimOrNull(form.nombre),
      nombre_preferido: trimOrNull(form.nombre_preferido),
      apellido_paterno: trimOrNull(form.apellido_paterno),
      apellido_materno: trimOrNull(form.apellido_materno),
      telefono_1: trimOrNull(form.telefono_1),
      tipo_telefono_1: form.tipo_telefono_1,
      celular: trimOrNull(form.celular),
      tipo_telefono_2: form.tipo_telefono_2,
      correo_electronico: trimOrNull(form.correo_electronico),
      metodo_confirmacion: form.metodo_confirmacion || null,
      fecha_nacimiento: form.fecha_nacimiento || null,
      medico_id: medicoId.value,
    };
    if (selected.value) {
      await updatePaciente(selected.value.id, medicoId.value, payload);
      message.value = 'Paciente actualizado.';
    } else {
      await createPaciente(payload);
      message.value = 'Paciente creado.';
    }
    setForm(null);
    await load();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible guardar el paciente.';
  }
}

function confirmationMethodLabel(paciente: Paciente) {
  if (!paciente.metodo_confirmacion) return '-';
  return (
    buildConfirmationMethodOptions(paciente).find((option) => option.value === paciente.metodo_confirmacion)?.label ??
    paciente.metodo_confirmacion
  );
}

function phoneLabel(type: PhoneType, value?: string | null) {
  return value ? `${type === 'FIJO' ? 'Fijo' : 'Celular'} · ${value}` : '-';
}

async function setActive(active: boolean) {
  if (!selected.value || !medicoId.value) return;
  error.value = '';
  message.value = '';
  try {
    selected.value = active
      ? await activatePaciente(selected.value.id, medicoId.value)
      : await deactivatePaciente(selected.value.id, medicoId.value);
    message.value = active ? 'Paciente activado.' : 'Paciente desactivado.';
    await load();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cambiar el estado.';
  }
}

async function markForDeletion() {
  if (!selected.value || !medicoId.value) return;
  error.value = '';
  message.value = '';
  try {
    selected.value = await markPacienteForDeletion(selected.value.id, medicoId.value);
    message.value = 'Paciente marcado para borrar.';
    await load();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible marcar para borrar.';
  }
}

async function loadMedicos() {
  loading.value = true;
  error.value = '';
  try {
    const [userData, medicosData] = await Promise.all([getCurrentUser(), listAccessibleMedicos()]);
    currentUser.value = userData;
    medicos.value = medicosData;
    const defaultId = defaultMedicoId();
    if (defaultId && !medicoId.value) {
      setMedicoSelection(defaultId);
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No fue posible cargar médicos.';
  } finally {
    loading.value = false;
  }
}

async function onMedicoChange() {
  query.value = '';
  message.value = '';
  setForm(null);
  await load();
}

onMounted(async () => {
  await loadMedicos();
  await load();
});
</script>

<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1>Pacientes</h1>
        <p>Alta, búsqueda y control operativo sin datos clínicos.</p>
      </div>
    </div>

    <section class="panel">
      <div class="form-row">
        <label for="medico-pacientes">Médico</label>
        <select
          id="medico-pacientes"
          v-model="medicoId"
          :disabled="medicos.length === 0"
          @change="onMedicoChange"
        >
          <option value="">Selecciona médico</option>
          <option v-for="medico in medicos" :key="medico.id" :value="medico.id">{{ medicoLabel(medico) }}</option>
        </select>
      </div>
    </section>

    <div class="grid catalog-grid">
      <form class="panel form compact-form" @submit.prevent="submit()">
        <h2>{{ selected ? 'Editar paciente' : 'Crear paciente' }}</h2>
        <p v-if="!canEditPatient" class="message">Selecciona un médico para habilitar la creación de pacientes.</p>
        <fieldset class="fieldset-reset" :disabled="!canEditPatient">
          <div class="form-row">
            <label for="nombre">Nombre</label>
            <input id="nombre" v-model="form.nombre" :required="!form.nombre_preferido.trim()" maxlength="180" />
          </div>
          <div class="form-row">
            <label for="nombre_preferido">Nombre preferido</label>
            <input id="nombre_preferido" v-model="form.nombre_preferido" maxlength="60" @input="confirmPreferredOnly = false" />
          </div>
          <div class="form-row">
            <label for="apellido_paterno">Apellido paterno</label>
            <input id="apellido_paterno" v-model="form.apellido_paterno" :required="!form.nombre_preferido.trim()" maxlength="180" />
          </div>
          <div class="form-row">
            <label for="apellido_materno">Apellido materno</label>
            <input id="apellido_materno" v-model="form.apellido_materno" maxlength="180" />
          </div>
          <div class="form-row">
            <label for="tipo_telefono_1">Tipo de teléfono 1</label>
            <select id="tipo_telefono_1" v-model="form.tipo_telefono_1">
              <option value="FIJO">Fijo</option>
              <option value="CELULAR">Celular</option>
            </select>
          </div>
          <div class="form-row">
            <label for="telefono_1">Teléfono 1</label>
            <input id="telefono_1" v-model="form.telefono_1" autocomplete="tel" inputmode="tel" maxlength="40" required />
          </div>
          <div class="form-row">
            <label for="tipo_telefono_2">Tipo de teléfono 2</label>
            <select id="tipo_telefono_2" v-model="form.tipo_telefono_2">
              <option value="FIJO">Fijo</option>
              <option value="CELULAR">Celular</option>
            </select>
          </div>
          <div class="form-row">
            <label for="celular">Teléfono 2</label>
            <input id="celular" v-model="form.celular" autocomplete="tel" inputmode="tel" maxlength="40" required />
          </div>
          <div class="form-row">
            <label for="correo_electronico">Correo electrónico</label>
            <input id="correo_electronico" v-model="form.correo_electronico" autocomplete="email" maxlength="320" type="email" />
          </div>
          <div class="form-row">
            <label for="metodo_confirmacion">Método de envío y confirmación de citas</label>
            <select id="metodo_confirmacion" v-model="form.metodo_confirmacion">
              <option value="">Sin seleccionar</option>
              <option v-for="option in confirmationMethodOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </div>
          <div class="form-row">
            <label for="fecha_nacimiento">Fecha de nacimiento</label>
            <div class="date-segments">
              <input
                id="fecha_nacimiento"
                ref="birthYearInput"
                v-model="birthDate.year"
                aria-label="Año de nacimiento"
                inputmode="numeric"
                maxlength="4"
                placeholder="AAAA"
                @input="handleBirthDateInput('year', 4, 'month')"
              />
              <input
                ref="birthMonthInput"
                v-model="birthDate.month"
                aria-label="Mes de nacimiento"
                inputmode="numeric"
                maxlength="2"
                placeholder="MM"
                @input="handleBirthDateInput('month', 2, 'day')"
              />
              <input
                ref="birthDayInput"
                v-model="birthDate.day"
                aria-label="Día de nacimiento"
                inputmode="numeric"
                maxlength="2"
                placeholder="DD"
                @input="handleBirthDateInput('day', 2)"
              />
            </div>
          </div>
          <div v-if="confirmPreferredOnly" class="duplicate-warning">
            <strong>Solo se capturó nombre preferido, ¿Continuar?</strong>
            <div class="actions-row">
              <button class="success" type="button" @click="submit(true)">Sí</button>
              <button class="danger solid" type="button" @click="confirmPreferredOnly = false">No</button>
            </div>
          </div>
          <div class="actions-row">
            <button type="submit">{{ selected ? 'Guardar cambios' : 'Crear paciente' }}</button>
            <button v-if="selected" class="secondary" type="button" @click="setForm(null)">Nuevo</button>
            <button v-if="selected?.activo" class="danger" type="button" @click="setActive(false)">Desactivar</button>
            <button v-else-if="selected" class="secondary" type="button" @click="setActive(true)">Activar</button>
            <button v-if="selected" class="danger" type="button" @click="markForDeletion">Marcar para borrar</button>
          </div>
        </fieldset>
        <p v-if="message" class="message">{{ message }}</p>
        <p v-if="error" class="error">{{ error }}</p>
      </form>

      <div class="panel table-panel">
        <div class="page-header compact">
          <h2>Listado</h2>
          <form class="inline-actions" @submit.prevent="search">
            <input v-model="query" placeholder="Nombre, teléfono, correo o folio" />
            <button type="submit">Buscar</button>
            <button class="secondary" type="button" @click="query = ''; load()">Limpiar</button>
          </form>
        </div>
        <p v-if="!canEditPatient" class="message">Selecciona un médico para cargar pacientes.</p>
        <p v-if="loading" class="message">Cargando...</p>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Folio</th>
                <th>Paciente</th>
                <th>Nombre preferido</th>
                <th>Fecha de nacimiento</th>
                <th>Teléfono 1</th>
                <th>Teléfono 2</th>
                <th>Correo electrónico</th>
                <th>Método de confirmación</th>
                <th>Estado</th>
                <th>Marcar borrar</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="paciente in sortedPacientes"
                :key="paciente.id"
                class="selectable-row"
                :class="{ selected: selected?.id === paciente.id }"
                @click="setForm(paciente)"
              >
                <td>{{ paciente.folio_paciente }}</td>
                <td>{{ patientDisplayName(paciente) }}</td>
                <td>{{ paciente.nombre_preferido || '-' }}</td>
                <td>{{ paciente.fecha_nacimiento || '-' }}</td>
                <td>{{ phoneLabel(paciente.tipo_telefono_1, paciente.telefono_1) }}</td>
                <td>{{ phoneLabel(paciente.tipo_telefono_2, paciente.celular) }}</td>
                <td>{{ paciente.correo_electronico || '-' }}</td>
                <td>{{ confirmationMethodLabel(paciente) }}</td>
                <td>
                  <span class="status" :class="paciente.activo ? 'ok' : 'muted'">
                    {{ paciente.activo ? 'Activo' : `Inactivo ${paciente.desactivado_en ? new Date(paciente.desactivado_en).toLocaleString() : ''}` }}
                  </span>
                </td>
                <td>{{ paciente.marcado_borrado_en ? new Date(paciente.marcado_borrado_en).toLocaleString() : '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>
</template>
