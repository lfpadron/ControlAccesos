export type FieldType = 'text' | 'email' | 'password' | 'textarea' | 'number' | 'select' | 'multiselect' | 'checkbox';

export type LookupKey =
  | 'instituciones'
  | 'complejos'
  | 'usuarios'
  | 'roles'
  | 'torres'
  | 'pisos'
  | 'clusters-turnos'
  | 'consultorios'
  | 'medicos'
  | 'operadores';

export type CatalogField = {
  name: string;
  label: string;
  type?: FieldType;
  required?: boolean;
  minLength?: number;
  maxLength?: number;
  min?: number;
  max?: number;
  pattern?: string;
  title?: string;
  lookup?: LookupKey;
  options?: Array<{ value: string; label: string }>;
  createOnly?: boolean;
  editOptional?: boolean;
  transient?: boolean;
  defaultValue?: string | number | boolean | null;
};

export type CatalogColumn = {
  name: string;
  label: string;
  lookup?: LookupKey;
  options?: Array<{ value: string; label: string }>;
  boolean?: boolean;
  trueLabel?: string;
  falseLabel?: string;
};

export type CatalogConfig = {
  key: string;
  title: string;
  description: string;
  resource: string;
  entityName: string;
  activeField?: 'activo' | 'activa';
  institutionScoped?: boolean;
  showCancelOnCreate?: boolean;
  fields: CatalogField[];
  columns: CatalogColumn[];
};

export const turnoTemplateOptions = [
  { value: 'PACIENTE_CONSULTORIO', label: 'Paciente Juan P* a consultorio C19' },
  { value: 'TURNO_PACIENTE_CONSULTORIO', label: 'Turno ABCD del paciente Juan P* a consultorio C19' },
  { value: 'PACIENTE_TURNO_CONSULTORIO', label: 'Paciente Juan P* con turno ABCD a consultorio C19' },
  { value: 'TURNO_CONSULTORIO', label: 'Turno ABCD a consultorio C19' },
];

export const catalogs: Record<string, CatalogConfig> = {
  roles: {
    key: 'roles',
    title: 'Roles',
    description: 'Permisos base para la operación y administración del sistema.',
    resource: 'roles',
    entityName: 'rol',
    activeField: 'activo',
    fields: [
      { name: 'codigo', label: 'Código', required: true, maxLength: 80 },
      { name: 'nombre', label: 'Nombre', required: true, maxLength: 180 },
      { name: 'descripcion', label: 'Descripción', type: 'textarea' },
      { name: 'activo', label: 'Activo', type: 'checkbox', defaultValue: true },
    ],
    columns: [
      { name: 'codigo', label: 'Código' },
      { name: 'nombre', label: 'Nombre' },
      { name: 'activo', label: 'Estado', boolean: true },
    ],
  },
  usuarios: {
    key: 'usuarios',
    title: 'Usuarios',
    description: 'Cuentas de acceso para administradores, médicos y personal operativo.',
    resource: 'usuarios',
    entityName: 'usuario',
    fields: [
      { name: 'nombre', label: 'Nombre', required: true, maxLength: 180 },
      { name: 'email', label: 'Correo electrónico', type: 'email', required: true, maxLength: 255 },
      {
        name: 'password',
        label: 'Contraseña temporal / nueva',
        type: 'password',
        required: true,
        minLength: 8,
        maxLength: 128,
        pattern: '^(?=.*\\d).{8,128}$',
        title: 'La contraseña debe tener al menos 8 caracteres y al menos 1 número.',
        editOptional: true,
      },
      { name: 'telefono', label: 'Teléfono', maxLength: 64 },
      { name: 'force_password_change', label: 'Forzar cambio de contraseña', type: 'checkbox', defaultValue: false },
      { name: 'estado', label: 'Estado', defaultValue: 'ACTIVO', maxLength: 40 },
    ],
    columns: [
      { name: 'nombre', label: 'Nombre' },
      { name: 'email', label: 'Correo' },
      { name: 'force_password_change', label: 'Cambio requerido', boolean: true },
      { name: 'estado', label: 'Estado' },
    ],
  },
  'usuario-roles': {
    key: 'usuario-roles',
    title: 'Roles de Usuario',
    description: 'Asignación de roles globales o acotados por institución y campus.',
    resource: 'usuario-roles',
    entityName: 'asignación de rol',
    activeField: 'activo',
    fields: [
      { name: 'usuario_id', label: 'Usuario', type: 'select', lookup: 'usuarios', required: true },
      { name: 'rol_id', label: 'Rol', type: 'select', lookup: 'roles', required: true },
      { name: 'institucion_id', label: 'Institución', type: 'select', lookup: 'instituciones' },
      { name: 'complejo_id', label: 'Campus', type: 'select', lookup: 'complejos' },
      { name: 'activo', label: 'Activo', type: 'checkbox', defaultValue: true },
    ],
    columns: [
      { name: 'usuario_id', label: 'Usuario', lookup: 'usuarios' },
      { name: 'rol_id', label: 'Rol', lookup: 'roles' },
      { name: 'institucion_id', label: 'Institución', lookup: 'instituciones' },
      { name: 'complejo_id', label: 'Campus', lookup: 'complejos' },
      { name: 'activo', label: 'Estado', boolean: true },
    ],
  },
  torres: {
    key: 'torres',
    title: 'Torres',
    description: 'Torres asociadas a cada campus y su capacidad de pisos.',
    resource: 'torres',
    entityName: 'torre',
    activeField: 'activo',
    institutionScoped: true,
    showCancelOnCreate: true,
    fields: [
      { name: 'complejo_id', label: 'Campus', type: 'select', lookup: 'complejos', required: true },
      { name: 'nombre', label: 'Nombre', required: true, maxLength: 180 },
      { name: 'descripcion', label: 'Descripción', type: 'textarea' },
      { name: 'numero_pisos', label: 'Número de pisos', type: 'number', required: true, defaultValue: 1 },
      { name: 'activo', label: 'Activo', type: 'checkbox', defaultValue: true },
    ],
    columns: [
      { name: 'nombre', label: 'Nombre' },
      { name: 'complejo_id', label: 'Campus', lookup: 'complejos' },
      { name: 'numero_pisos', label: 'Número de pisos' },
      { name: 'activo', label: 'Estado', boolean: true },
    ],
  },
  pisos: {
    key: 'pisos',
    title: 'Pisos',
    description: 'Catálogo físico de niveles dentro de cada campus.',
    resource: 'pisos',
    entityName: 'piso',
    activeField: 'activo',
    institutionScoped: true,
    showCancelOnCreate: true,
    fields: [
      { name: 'complejo_id', label: 'Campus', type: 'select', lookup: 'complejos', required: true },
      { name: 'torre_id', label: 'Torre', type: 'select', lookup: 'torres', required: true },
      { name: 'numero', label: 'Número de piso', type: 'number' },
      { name: 'codigo', label: 'Código de piso', maxLength: 40 },
      { name: 'nombre_visible', label: 'Nombre visible', required: true, maxLength: 20 },
      { name: 'descripcion', label: 'Descripción', type: 'textarea', maxLength: 200 },
      { name: 'cuenta_con_pantallas', label: 'Cuenta con pantallas', type: 'checkbox', defaultValue: false },
      { name: 'activo', label: 'Activo', type: 'checkbox', defaultValue: true },
    ],
    columns: [
      { name: 'complejo_id', label: 'Campus', lookup: 'complejos' },
      { name: 'torre_id', label: 'Torre', lookup: 'torres' },
      { name: 'numero', label: 'Número de piso' },
      { name: 'codigo', label: 'Código de piso' },
      { name: 'nombre_visible', label: 'Nombre visible' },
      { name: 'cuenta_con_pantallas', label: 'Cuenta con pantallas', boolean: true },
      { name: 'activo', label: 'Estado', boolean: true },
    ],
  },
  'salas-espera': {
    key: 'salas-espera',
    title: 'Salas de Espera',
    description: 'Áreas donde recepción, kiosko y operación pueden ubicar visitantes.',
    resource: 'salas-espera',
    entityName: 'sala de espera',
    activeField: 'activa',
    institutionScoped: true,
    showCancelOnCreate: true,
    fields: [
      { name: 'complejo_id', label: 'Campus', type: 'select', lookup: 'complejos', required: true },
      { name: 'torre_id', label: 'Torre', type: 'select', lookup: 'torres', required: true, transient: true },
      { name: 'piso_id', label: 'Piso', type: 'select', lookup: 'pisos', required: true },
      { name: 'nombre', label: 'Nombre', required: true, maxLength: 180 },
      { name: 'descripcion', label: 'Descripción', type: 'textarea' },
      { name: 'capacidad_estimada', label: 'Capacidad estimada', type: 'number' },
      { name: 'activa', label: 'Activa', type: 'checkbox', defaultValue: true },
    ],
    columns: [
      { name: 'nombre', label: 'Nombre' },
      { name: 'complejo_id', label: 'Campus', lookup: 'complejos' },
      { name: 'piso_id', label: 'Piso', lookup: 'pisos' },
      { name: 'activa', label: 'Estado', boolean: true },
    ],
  },
  'clusters-turnos': {
    key: 'clusters-turnos',
    title: 'Clústers',
    description: 'Agrupaciones de despliegue para pantallas de turnos dentro de cada piso.',
    resource: 'clusters-turnos',
    entityName: 'clúster',
    activeField: 'activo',
    institutionScoped: true,
    showCancelOnCreate: true,
    fields: [
      { name: 'complejo_id', label: 'Campus', type: 'select', lookup: 'complejos', required: true },
      { name: 'torre_id', label: 'Torre', type: 'select', lookup: 'torres', required: true, transient: true },
      { name: 'piso_id', label: 'Piso', type: 'select', lookup: 'pisos', required: true },
      { name: 'nombre', label: 'Nombre', required: true, maxLength: 180 },
      { name: 'muestra_turnos', label: 'Turnos', type: 'checkbox', defaultValue: true },
      { name: 'muestra_proxima_cita', label: 'Próxima cita', type: 'checkbox', defaultValue: false },
      { name: 'max_citas_proximas', label: 'Máximo de citas', type: 'number', required: true, defaultValue: 10, min: 5, max: 50 },
      { name: 'descripcion', label: 'Descripción', type: 'textarea' },
      { name: 'activo', label: 'Activo', type: 'checkbox', defaultValue: true },
    ],
    columns: [
      { name: 'nombre', label: 'Nombre' },
      { name: 'complejo_id', label: 'Campus', lookup: 'complejos' },
      { name: 'piso_id', label: 'Piso', lookup: 'pisos' },
      { name: 'muestra_turnos', label: 'Turno', boolean: true, trueLabel: 'Sí', falseLabel: 'No' },
      { name: 'muestra_proxima_cita', label: 'Próxima cita', boolean: true, trueLabel: 'Sí', falseLabel: 'No' },
      { name: 'max_citas_proximas', label: 'Máximo de citas' },
      { name: 'activo', label: 'Estado', boolean: true },
    ],
  },
  consultorios: {
    key: 'consultorios',
    title: 'Consultorios',
    description: 'Espacios físicos disponibles para asignación médica.',
    resource: 'consultorios',
    entityName: 'consultorio',
    activeField: 'activo',
    institutionScoped: true,
    showCancelOnCreate: true,
    fields: [
      { name: 'complejo_id', label: 'Campus', type: 'select', lookup: 'complejos', required: true },
      { name: 'torre_id', label: 'Torre', type: 'select', lookup: 'torres', required: true, transient: true },
      { name: 'piso_id', label: 'Piso', type: 'select', lookup: 'pisos', required: true },
      { name: 'codigo', label: 'Código', required: true, maxLength: 80 },
      { name: 'nombre_visible', label: 'Nombre visible', maxLength: 180 },
      { name: 'instrucciones_acceso', label: 'Instrucciones de acceso', type: 'textarea' },
      { name: 'notas', label: 'Notas', type: 'textarea', maxLength: 1000 },
      { name: 'cluster_ids', label: 'Clústers', type: 'multiselect', lookup: 'clusters-turnos', required: true },
      { name: 'activo', label: 'Activo', type: 'checkbox', defaultValue: true },
    ],
    columns: [
      { name: 'codigo', label: 'Código' },
      { name: 'nombre_visible', label: 'Nombre visible' },
      { name: 'complejo_id', label: 'Campus', lookup: 'complejos' },
      { name: 'piso_id', label: 'Piso', lookup: 'pisos' },
      { name: 'cluster_ids', label: 'Clústers', lookup: 'clusters-turnos' },
      { name: 'activo', label: 'Estado', boolean: true },
    ],
  },
  medicos: {
    key: 'medicos',
    title: 'Médicos',
    description: 'Directorio operativo de médicos que podrán recibir asignaciones.',
    resource: 'medicos',
    entityName: 'médico',
    activeField: 'activo',
    fields: [
      { name: 'usuario_id', label: 'Usuario asociado', type: 'select', lookup: 'usuarios' },
      { name: 'nombre', label: 'Nombre', required: true, maxLength: 180 },
      { name: 'apellidos', label: 'Apellidos', required: true, maxLength: 180 },
      { name: 'nombre_visible', label: 'Nombre visible', maxLength: 220 },
      {
        name: 'plantilla_turno',
        label: 'Plantilla de llamada',
        type: 'select',
        required: true,
        defaultValue: 'PACIENTE_CONSULTORIO',
        options: turnoTemplateOptions,
      },
      { name: 'activo', label: 'Activo', type: 'checkbox', defaultValue: true },
    ],
    columns: [
      { name: 'nombre_visible', label: 'Nombre visible' },
      { name: 'nombre', label: 'Nombre' },
      { name: 'apellidos', label: 'Apellidos' },
      { name: 'plantilla_turno', label: 'Plantilla de llamada', options: turnoTemplateOptions },
      { name: 'usuario_id', label: 'Usuario', lookup: 'usuarios' },
      { name: 'activo', label: 'Estado', boolean: true },
    ],
  },
  operadores: {
    key: 'operadores',
    title: 'Operadores',
    description: 'Personal operativo que podrá apoyar médicos, consultorios o campus.',
    resource: 'operadores',
    entityName: 'operador',
    activeField: 'activo',
    fields: [
      { name: 'usuario_id', label: 'Usuario', type: 'select', lookup: 'usuarios', required: true },
      { name: 'activo', label: 'Activo', type: 'checkbox', defaultValue: true },
    ],
    columns: [
      { name: 'usuario_id', label: 'Usuario', lookup: 'usuarios' },
      { name: 'activo', label: 'Estado', boolean: true },
    ],
  },
  'pantallas-turnos': {
    key: 'pantallas-turnos',
    title: 'Pantallas de Turnos',
    description: 'Configuración visual y alcance físico de las pantallas públicas.',
    resource: 'pantallas-turnos',
    entityName: 'pantalla',
    activeField: 'activa',
    fields: [
      { name: 'codigo_dispositivo', label: 'Código de dispositivo', required: true, maxLength: 120 },
      { name: 'token', label: 'Token de dispositivo', type: 'password', createOnly: true },
      { name: 'nombre', label: 'Nombre', maxLength: 180 },
      { name: 'complejo_id', label: 'Campus', type: 'select', lookup: 'complejos', required: true },
      { name: 'piso_id', label: 'Piso', type: 'select', lookup: 'pisos' },
      { name: 'cluster_espera_id', label: 'Clúster de espera' },
      { name: 'consultorio_id', label: 'Consultorio', type: 'select', lookup: 'consultorios' },
      { name: 'polling_interval_seconds', label: 'Polling (segundos)', type: 'number', defaultValue: 5 },
      { name: 'segundos_resaltado', label: 'Segundos resaltado', type: 'number', defaultValue: 25 },
      { name: 'segundos_visible', label: 'Segundos visible', type: 'number', defaultValue: 300 },
      { name: 'color_fondo', label: 'Color de fondo' },
      { name: 'color_texto', label: 'Color de texto' },
      { name: 'color_turno_nuevo', label: 'Color de turno nuevo' },
      { name: 'color_turno_normal', label: 'Color de turno normal' },
      { name: 'font_size_turno_nuevo', label: 'Tamaño turno nuevo', type: 'number' },
      { name: 'font_size_turno_normal', label: 'Tamaño turno normal', type: 'number' },
      { name: 'activa', label: 'Activa', type: 'checkbox', defaultValue: true },
    ],
    columns: [
      { name: 'codigo_dispositivo', label: 'Código' },
      { name: 'nombre', label: 'Nombre' },
      { name: 'complejo_id', label: 'Campus', lookup: 'complejos' },
      { name: 'piso_id', label: 'Piso', lookup: 'pisos' },
      { name: 'polling_interval_seconds', label: 'Polling' },
      { name: 'activa', label: 'Estado', boolean: true },
    ],
  },
};
