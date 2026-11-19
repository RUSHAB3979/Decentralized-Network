import { ORCHESTRATOR_URL } from './api';
import { authRequest } from './authApi';

export const PROVIDER_TOKEN_KEY = 'nodeforge.provider-session';
const PROVIDER_BASE_URL = `${ORCHESTRATOR_URL}/v1/provider`;
const PROVIDER_TIMEOUT_MS = 60_000;

export function storedProviderToken() {
  try {
    return window.localStorage.getItem(PROVIDER_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function saveProviderToken(token) {
  try {
    window.localStorage.setItem(PROVIDER_TOKEN_KEY, token);
  } catch {
    // The current tab can still keep its session in memory.
  }
}

export function clearProviderToken(token) {
  try {
    if (storedProviderToken() === token) window.localStorage.removeItem(PROVIDER_TOKEN_KEY);
  } catch {
    // Storage can be unavailable in private browsing.
  }
}

function request(path, { signal, ...options } = {}) {
  const timeout = AbortSignal.timeout(PROVIDER_TIMEOUT_MS);
  return authRequest(path, {
    ...options,
    baseUrl: PROVIDER_BASE_URL,
    signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
  });
}

export function authenticateProvider(mode, { email, password, displayName }) {
  const body = { email, password };
  if (mode === 'signup') body.display_name = displayName.trim() || null;
  return request(`/auth/${mode}`, { body });
}

export const fetchProviderProfile = (token, signal) =>
  request('/auth/me', { method: 'GET', token, signal });

export const logoutProvider = (token) => request('/auth/logout', { token });

export const fetchOwnedNodes = (token, signal) =>
  request('/nodes', { method: 'GET', token, signal });

export const fetchProviderJobs = (token, signal) =>
  request('/jobs', { method: 'GET', token, signal });

export const revokeOwnedNode = (token, nodeId) =>
  request(`/nodes/${encodeURIComponent(nodeId)}`, { method: 'DELETE', token });

export const fetchEnrolmentKeys = (token, signal) =>
  request('/enrolment-keys', { method: 'GET', token, signal });

export const mintEnrolmentKey = (token) => request('/enrolment-keys', { token });

export const revokeEnrolmentKey = (token, keyId) =>
  request(`/enrolment-keys/${encodeURIComponent(keyId)}`, { method: 'DELETE', token });
