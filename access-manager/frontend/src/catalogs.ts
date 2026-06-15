export type FieldType = 'text' | 'email' | 'password' | 'textarea' | 'number' | 'select' | 'multiselect' | 'checkbox';

export type LookupKey =
  | 'instituciones'
  | 'complejos'
  | 'usuarios'
  | 'roles'
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
  maxLength?: number;
  lookup?: LookupKey;
  createOnly?: boolean;
  defaultValue?: string | number | boolean | null;
};

export type CatalogColumn = {
  name: string;
  label: string;
  lookup?: LookupKey;
  boolean?: boolean;
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
      { name: 'password', label: 'Contraseña temporal', type: 'password', required: true, createOnly: true },
      { name: 'telefono', label: 'Teléfono', maxLength: 64 },
      { name: 'estado', label: 'Estado', defaultValue: 'ACTIVO', maxLength: 40 },
    ],
    columns: [
      { name: 'nombre', label: 'Nombre' },
      { name: 'email', label: 'Correo' },
      { name: 'estado', label: 'Estado' },
    ],
  },
  'usuario-roles': {
    key: 'usuario-roles',
    title: 'Roles de Usuario',
    description: 'Asignación de roles globales o acotados por institución y complejo.',
    resource: 'usuario-roles',
    entityName: 'asignación de rol',
    activeField: 'activo',
    fields: [
      { name: 'usuario_id', label: 'Usuario', type: 'select', lookup: 'usuarios', required: true },
      { name: 'rol_id', label: 'Rol', type: 'select', lookup: 'roles', required: true },
      { name: 'institucion_id', label: 'Institución', type: 'select', lookup: 'instituciones' },
      { name: 'complejo_id', label: 'Complejo', type: 'select', lookup: 'complejos' },
      { name: 'activo', label: 'Activo', type: 'checkbox', defaultValue: true },
    ],
    columns: [
      { name: 'usuario_id', label: 'Usuario', lookup: 'usuarios' },
      { name: 'rol_id', label: 'Rol', lookup: 'roles' },
      { name: 'institucion_id', label: 'Institución', lookup: 'instituciones' },
      { name: 'complejo_id', label: 'Complejo', lookup: 'complejos' },
      { name: 'activo', label: 'Estado', boolean: true },
    ],
  },
  pisos: {
    key: 'pisos',
    title: 'Pisos',
    description: 'Catálogo físico de niveles dentro de cada complejo.',
    resource: 'pisos',
    entityName: 'piso',
    activeField: 'activo',
    institutionScoped: true,
    showCancelOnCreate: true,
    fields: [
      { name: 'complejo_id', label: 'Complejo', type: 'select', lookup: 'complejos', required: true },
      { name: 'numero', label: 'Número', required: true, maxLength: 40 },
      { name: 'nombre_visible', label: 'Nombre visible', required: true, maxLength: 180 },
      { name: 'descripcion', label: 'Descripción', type: 'textarea' },
      { name: 'activo', label: 'Activo', type: 'checkbox', defaultValue: true },
    ],
    columns: [
      { name: 'complejo_id', label: 'Complejo', lookup: 'complejos' },
      { name: 'numero', label: 'Número' },
      { name: 'nombre_visible', label: 'Nombre visible' },
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
      { name: 'complejo_id', label: 'Complejo', type: 'select', lookup: 'complejos', required: true },
      { name: 'piso_id', label: 'Piso', type: 'select', lookup: 'pisos', required: true },
      { name: 'nombre', label: 'Nombre', required: true, maxLength: 180 },
      { name: 'descripcion', label: 'Descripción', type: 'textarea' },
      { name: 'capacidad_estimada', label: 'Capacidad estimada', type: 'number' },
      { name: 'activa', label: 'Activa', type: 'checkbox', defaultValue: true },
    ],
    columns: [
      { name: 'nombre', label: 'Nombre' },
      { name: 'complejo_id', label: 'Complejo', lookup: 'complejos' },
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
      { name: 'complejo_id', label: 'Complejo', type: 'select', lookup: 'complejos', required: true },
      { name: 'piso_id', label: 'Piso', type: 'select', lookup: 'pisos', required: true },
      { name: 'nombre', label: 'Nombre', required: true, maxLength: 180 },
      { name: 'descripcion', label: 'Descripción', type: 'textarea' },
      { name: 'activo', label: 'Activo', type: 'checkbox', defaultValue: true },
    ],
    columns: [
      { name: 'nombre', label: 'Nombre' },
      { name: 'complejo_id', label: 'Complejo', lookup: 'complejos' },
      { name: 'piso_id', label: 'Piso', lookup: 'pisos' },
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
      { name: 'complejo_id', label: 'Complejo', type: 'select', lookup: 'complejos', required: true },
      { name: 'piso_id', label: 'Piso', type: 'select', lookup: 'pisos', required: true },
      { name: 'codigo', label: 'Código', required: true, maxLength: 80 },
      { name: 'nombre_visible', label: 'Nombre visible', maxLength: 180 },
      { name: 'instrucciones_acceso', label: 'Instrucciones de acceso', type: 'textarea' },
      { name: 'cluster_ids', label: 'Clústers', type: 'multiselect', lookup: 'clusters-turnos', required: true },
      { name: 'activo', label: 'Activo', type: 'checkbox', defaultValue: true },
    ],
    columns: [
      { name: 'codigo', label: 'Código' },
      { name: 'nombre_visible', label: 'Nombre visible' },
      { name: 'complejo_id', label: 'Complejo', lookup: 'complejos' },
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
      { name: 'activo', label: 'Activo', type: 'checkbox', defaultValue: true },
    ],
    columns: [
      { name: 'nombre_visible', label: 'Nombre visible' },
      { name: 'nombre', label: 'Nombre' },
      { name: 'apellidos', label: 'Apellidos' },
      { name: 'usuario_id', label: 'Usuario', lookup: 'usuarios' },
      { name: 'activo', label: 'Estado', boolean: true },
    ],
  },
  operadores: {
    key: 'operadores',
    title: 'Operadores',
    description: 'Personal operativo que podrá apoyar médicos, consultorios o complejos.',
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
      { name: 'complejo_id', label: 'Complejo', type: 'select', lookup: 'complejos', required: true },
      { name: 'piso_id', label: 'Piso', type: 'select', lookup: 'pisos' },
      { name: 'cluster_espera_id', label: 'Clúster de espera' },
      { name: 'consultorio_id', label: 'Consultorio', type: 'select', lookup: 'consultorios' },
      { name: 'polling_interval_seconds', label: 'Polling (segundos)', type: 'number', defaultValue: 5 },
      { name: 'segundos_resaltado', label: 'Segundos resaltado', type: 'number', defaultValue: 25 },
      { name: 'segundos_visible', label: 'Segundos visible', type: 'number', defaultValue: 300 },
      { name: 'max_turnos_visibles', label: 'Máximo de turnos visibles', type: 'number', defaultValue: 10 },
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
      { name: 'complejo_id', label: 'Complejo', lookup: 'complejos' },
      { name: 'piso_id', label: 'Piso', lookup: 'pisos' },
      { name: 'polling_interval_seconds', label: 'Polling' },
      { name: 'activa', label: 'Estado', boolean: true },
    ],
  },
};
