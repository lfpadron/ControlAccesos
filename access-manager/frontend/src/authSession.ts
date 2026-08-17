import { computed, ref } from 'vue';
import { clearToken, getCurrentUser, getToken, setToken, type Usuario } from './api/client';

const currentUserState = ref<Usuario | null>(null);
const authenticatedState = ref(Boolean(getToken()));

export const currentSessionUser = currentUserState;
export const isAuthenticated = computed(() => authenticatedState.value);

export function setSessionToken(token: string) {
  setToken(token);
  authenticatedState.value = true;
}

export function clearSession() {
  clearToken();
  authenticatedState.value = false;
  currentUserState.value = null;
}

export function setCurrentSessionUser(user: Usuario | null) {
  currentUserState.value = user;
  authenticatedState.value = Boolean(getToken());
}

export async function refreshCurrentSessionUser() {
  if (!getToken()) {
    setCurrentSessionUser(null);
    return null;
  }
  const user = await getCurrentUser();
  setCurrentSessionUser(user);
  return user;
}
