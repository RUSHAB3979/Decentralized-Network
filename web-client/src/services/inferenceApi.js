// The inference gateway, from the browser.
//
// Two different credentials talk to this API and they are not interchangeable,
// which is the thing to keep straight when reading this file:
//
//   session token  ->  /v1/api-keys        administering keys, as a person
//   API key        ->  /v1/models, /usage, /chat/completions   using the service
//
// Before accounts existed the key endpoints were unauthenticated and gated on
// the caller being loopback, so this file sent no credential at all for them.
// It now sends the session token, and a call made while signed out fails with
// 401 rather than quietly returning somebody else's keys.

import { ORCHESTRATOR_URL } from './api';
import { AuthError, storedToken } from './authApi';

export const INFERENCE_BASE_URL = `${ORCHESTRATOR_URL}/v1`;

async function apiRequest(path, { apiKey, useSession = false, ...options } = {}) {
  const headers = new Headers(options.headers ?? {});

  if (apiKey) {
    headers.set('Authorization', `Bearer ${apiKey}`);
  } else if (useSession) {
    const token = storedToken();
    // Fail here rather than sending an unauthenticated request. The server
    // would answer 401 either way, but a round trip to be told what we already
    // knew is a slower path to the same message.
    if (!token) throw new AuthError('You need to sign in first.', 401);
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  let response;
  try {
    response = await fetch(`${INFERENCE_BASE_URL}${path}`, { ...options, headers });
  } catch (cause) {
    // Same three indistinguishable causes as authApi.js -- see the note there.
    throw new AuthError(
      `Cannot reach the orchestrator at ${INFERENCE_BASE_URL}. It may still be `
      + `starting up, not deployed yet, or refusing this origin.`,
      0,
      { cause },
    );
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    // Carry the status through as AuthError so callers can tell a dead session
    // (401) from no capacity (503) from a missing model (404) without reading
    // the message. The gateway returns all three in normal operation and they
    // need three different responses from the UI.
    throw new AuthError(detail(body, response.status), response.status);
  }

  if (response.status === 204) return null;
  return response.json();
}

function detail(body, status) {
  const value = body?.detail;
  if (typeof value === 'string') return value;
  if (Array.isArray(value) && value.length) {
    const first = value[0];
    const field = Array.isArray(first?.loc) ? first.loc[first.loc.length - 1] : null;
    return field ? `${field}: ${first.msg}` : first.msg;
  }
  return `Gateway returned ${status}.`;
}

// --- key administration: needs a signed-in person -------------------------

export function listApiKeys() {
  return apiRequest('/api-keys', { useSession: true });
}

export function createApiKey(name = 'My key') {
  return apiRequest('/api-keys', {
    useSession: true,
    method: 'POST',
    body: JSON.stringify({ name }),
  });
}

export function revokeApiKey(keyId) {
  return apiRequest(`/api-keys/${encodeURIComponent(keyId)}`, {
    useSession: true,
    method: 'DELETE',
  });
}

// --- using the gateway: needs an API key ----------------------------------

export function fetchInferenceModels(apiKey) {
  return apiRequest('/models', { apiKey });
}

export function fetchInferenceUsage(apiKey) {
  return apiRequest('/usage', { apiKey });
}

export function createChatCompletion(apiKey, payload) {
  return apiRequest('/chat/completions', {
    apiKey,
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
