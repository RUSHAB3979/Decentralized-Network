import { ORCHESTRATOR_URL } from './api';

export const INFERENCE_BASE_URL = `${ORCHESTRATOR_URL}/v1`;

async function apiRequest(path, { apiKey, ...options } = {}) {
  const headers = new Headers(options.headers ?? {});
  if (apiKey) headers.set('Authorization', `Bearer ${apiKey}`);
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${INFERENCE_BASE_URL}${path}`, {
    ...options,
    headers,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `Gateway returned ${response.status}`);
  }
  if (response.status === 204) return null;
  return response.json();
}

export function listApiKeys() {
  return apiRequest('/api-keys');
}

export function createApiKey(name = 'Local demo key') {
  return apiRequest('/api-keys', {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
}

export function revokeApiKey(keyId) {
  return apiRequest(`/api-keys/${encodeURIComponent(keyId)}`, {
    method: 'DELETE',
  });
}

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
