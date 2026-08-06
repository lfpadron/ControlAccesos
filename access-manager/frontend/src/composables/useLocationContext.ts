import { computed, reactive } from 'vue';

const STORAGE_KEY = 'access-manager-location-context-v1';

export type LocationSelection = {
  id: string;
  label: string;
};

type LocationContextState = {
  institucion: LocationSelection | null;
  campus: LocationSelection | null;
  torre: LocationSelection | null;
  piso: LocationSelection | null;
};

type LocationContextSnapshot = Partial<LocationContextState>;

const fallbackState: LocationContextState = {
  institucion: null,
  campus: null,
  torre: null,
  piso: null,
};

function normalizeSelection(selection: LocationSelection | null | undefined) {
  if (!selection?.id) return null;
  return {
    id: selection.id,
    label: selection.label || selection.id,
  };
}

function loadState(): LocationContextState {
  if (typeof localStorage === 'undefined') {
    return { ...fallbackState };
  }
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return { ...fallbackState };
    const parsed = JSON.parse(stored) as LocationContextSnapshot;
    return {
      institucion: normalizeSelection(parsed.institucion),
      campus: normalizeSelection(parsed.campus),
      torre: normalizeSelection(parsed.torre),
      piso: normalizeSelection(parsed.piso),
    };
  } catch {
    return { ...fallbackState };
  }
}

const state = reactive<LocationContextState>(loadState());

function persist() {
  if (typeof localStorage === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function clearLocation() {
  state.institucion = null;
  state.campus = null;
  state.torre = null;
  state.piso = null;
  persist();
}

function setInstitution(selection: LocationSelection | null) {
  state.institucion = normalizeSelection(selection);
  state.campus = null;
  state.torre = null;
  state.piso = null;
  persist();
}

function setCampus(selection: LocationSelection | null, institution?: LocationSelection | null) {
  if (institution !== undefined) {
    state.institucion = normalizeSelection(institution);
  }
  state.campus = normalizeSelection(selection);
  state.torre = null;
  state.piso = null;
  persist();
}

function setTower(selection: LocationSelection | null, campus?: LocationSelection | null, institution?: LocationSelection | null) {
  if (institution !== undefined) {
    state.institucion = normalizeSelection(institution);
  }
  if (campus !== undefined) {
    state.campus = normalizeSelection(campus);
  }
  state.torre = normalizeSelection(selection);
  state.piso = null;
  persist();
}

function setFloor(
  selection: LocationSelection | null,
  tower?: LocationSelection | null,
  campus?: LocationSelection | null,
  institution?: LocationSelection | null,
) {
  if (institution !== undefined) {
    state.institucion = normalizeSelection(institution);
  }
  if (campus !== undefined) {
    state.campus = normalizeSelection(campus);
  }
  if (tower !== undefined) {
    state.torre = normalizeSelection(tower);
  }
  state.piso = normalizeSelection(selection);
  persist();
}

function clearCampus() {
  state.campus = null;
  state.torre = null;
  state.piso = null;
  persist();
}

function clearTower() {
  state.torre = null;
  state.piso = null;
  persist();
}

function clearFloor() {
  state.piso = null;
  persist();
}

function applyContext(snapshot: LocationContextSnapshot) {
  state.institucion = normalizeSelection(snapshot.institucion);
  state.campus = normalizeSelection(snapshot.campus);
  state.torre = normalizeSelection(snapshot.torre);
  state.piso = normalizeSelection(snapshot.piso);
  persist();
}

const pathText = computed(() =>
  [
    state.institucion?.label || 'Institución',
    state.campus?.label || 'Campus',
    state.torre?.label || 'Torre',
    state.piso?.label || 'Piso',
  ].join(' >> '),
);

export function useLocationContext() {
  return {
    locationContext: state,
    locationPathText: pathText,
    applyContext,
    clearCampus,
    clearFloor,
    clearLocation,
    clearTower,
    setCampus,
    setFloor,
    setInstitution,
    setTower,
  };
}
