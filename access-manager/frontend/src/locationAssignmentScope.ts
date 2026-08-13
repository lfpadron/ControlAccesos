import { getCurrentUser, listUsuarioRoles, type Complejo, type Consultorio, type Institucion, type Piso, type Torre, type Usuario, type UsuarioRol } from './api/client';

type InstitucionLike = Pick<Institucion, 'id'>;
type ComplejoLike = Pick<Complejo, 'id' | 'institucion_id'>;
type TorreLike = Pick<Torre, 'id' | 'complejo_id'>;
type PisoLike = Pick<Piso, 'id' | 'complejo_id' | 'torre_id'>;
type ConsultorioLike = Pick<Consultorio, 'id' | 'complejo_id' | 'piso_id'>;

export type UserLocationScopeInput = {
  currentUser: Usuario | null;
  usuarioRoles: UsuarioRol[];
  instituciones: InstitucionLike[];
  complejos: ComplejoLike[];
  torres: TorreLike[];
  pisos: PisoLike[];
  consultorios: ConsultorioLike[];
};

export type UserLocationScope = {
  allInstituciones: boolean;
  allComplejos: boolean;
  allTorres: boolean;
  institucionIds: Set<string>;
  complejoIds: Set<string>;
  torreIds: Set<string>;
};

export async function loadCurrentUserLocationAssignments() {
  const currentUser = await getCurrentUser();
  try {
    return {
      currentUser,
      usuarioRoles: await listUsuarioRoles(),
    };
  } catch {
    return {
      currentUser,
      usuarioRoles: [],
    };
  }
}

const emptyScope: UserLocationScope = {
  allInstituciones: true,
  allComplejos: true,
  allTorres: true,
  institucionIds: new Set(),
  complejoIds: new Set(),
  torreIds: new Set(),
};

function localDateText() {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

function isRoleActive(row: UsuarioRol, today = localDateText()) {
  return row.activo && row.fecha_inicio <= today && (!row.fecha_fin || row.fecha_fin >= today);
}

function hasLocationScope(row: UsuarioRol) {
  return Boolean(row.institucion_id || row.complejo_id || row.torre_id || row.piso_id || row.consultorio_id);
}

function hasGlobalLocationScope(row: UsuarioRol) {
  return !hasLocationScope(row) && !row.medico_id;
}

function allIfUnassigned(ids: Set<string>, rows: Array<{ id: string }>) {
  return ids.size === 0 || ids.size >= rows.length;
}

export function buildUserLocationScope(input: UserLocationScopeInput): UserLocationScope {
  const currentUser = input.currentUser;
  if (!currentUser || currentUser.role_codes?.includes('ADMIN_SISTEMA')) {
    return emptyScope;
  }

  const activeRows = input.usuarioRoles.filter((row) => row.usuario_id === currentUser.id && isRoleActive(row));
  const locationRows = activeRows.filter(hasLocationScope);
  if (activeRows.some(hasGlobalLocationScope) || locationRows.length === 0) {
    return emptyScope;
  }

  const institucionIds = new Set<string>();
  const complejoIds = new Set<string>();
  const torreIds = new Set<string>();
  const complejosById = new Map(input.complejos.map((item) => [item.id, item]));
  const torresById = new Map(input.torres.map((item) => [item.id, item]));
  const pisosById = new Map(input.pisos.map((item) => [item.id, item]));
  const consultoriosById = new Map(input.consultorios.map((item) => [item.id, item]));

  function addInstitucion(id: string | null | undefined) {
    if (id) institucionIds.add(id);
  }

  function addComplejo(id: string | null | undefined) {
    if (!id) return;
    const complejo = complejosById.get(id);
    if (!complejo) return;
    complejoIds.add(complejo.id);
    addInstitucion(complejo.institucion_id);
  }

  function addTorre(id: string | null | undefined) {
    if (!id) return;
    const torre = torresById.get(id);
    if (!torre) return;
    torreIds.add(torre.id);
    addComplejo(torre.complejo_id);
  }

  function addPiso(id: string | null | undefined) {
    if (!id) return;
    const piso = pisosById.get(id);
    if (!piso) return;
    addTorre(piso.torre_id);
    addComplejo(piso.complejo_id);
  }

  function addConsultorio(id: string | null | undefined) {
    if (!id) return;
    const consultorio = consultoriosById.get(id);
    if (!consultorio) return;
    addPiso(consultorio.piso_id);
    addComplejo(consultorio.complejo_id);
  }

  for (const row of locationRows) {
    if (row.institucion_id) {
      addInstitucion(row.institucion_id);
      for (const complejo of input.complejos.filter((item) => item.institucion_id === row.institucion_id)) {
        addComplejo(complejo.id);
      }
      for (const torre of input.torres.filter((item) => institucionIds.has(complejosById.get(item.complejo_id)?.institucion_id ?? ''))) {
        addTorre(torre.id);
      }
    }
    if (row.complejo_id) {
      addComplejo(row.complejo_id);
      for (const torre of input.torres.filter((item) => item.complejo_id === row.complejo_id)) {
        addTorre(torre.id);
      }
    }
    addTorre(row.torre_id);
    addPiso(row.piso_id);
    addConsultorio(row.consultorio_id);
  }

  return {
    allInstituciones: allIfUnassigned(institucionIds, input.instituciones),
    allComplejos: allIfUnassigned(complejoIds, input.complejos),
    allTorres: allIfUnassigned(torreIds, input.torres),
    institucionIds,
    complejoIds,
    torreIds,
  };
}

export function filterInstitucionesByUserAssignment<T extends { id: string }>(items: T[], scope: UserLocationScope) {
  if (scope.allInstituciones) return items;
  return items.filter((item) => scope.institucionIds.has(item.id));
}

export function filterComplejosByUserAssignment<T extends { id: string }>(items: T[], scope: UserLocationScope) {
  if (scope.allComplejos) return items;
  return items.filter((item) => scope.complejoIds.has(item.id));
}

export function filterTorresByUserAssignment<T extends { id: string }>(items: T[], scope: UserLocationScope) {
  if (scope.allTorres) return items;
  return items.filter((item) => scope.torreIds.has(item.id));
}
