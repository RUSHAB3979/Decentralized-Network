// Blender batch renders use the same authenticated customer session and base
// URL as the account and inference APIs. Project bytes are the exception: the
// browser sends them directly to object storage through a presigned URL.

import { ORCHESTRATOR_URL } from './api';
import { AuthError, storedToken } from './authApi';

export const RENDER_BASE_URL = `${ORCHESTRATOR_URL}/v1`;
export const RENDER_POLL_INTERVAL_MS = 8_000;
const RENDER_REQUEST_TIMEOUT_MS = 20_000;

const TERMINAL_STATUSES = new Set(['completed', 'failed', 'cancelled']);

export function isTerminalRenderStatus(status) {
  return TERMINAL_STATUSES.has(status);
}

async function renderRequest(path, { timeoutMs = RENDER_REQUEST_TIMEOUT_MS, ...options } = {}) {
  const token = storedToken();
  if (!token) throw new AuthError('You need to sign in first.', 401);

  const headers = new Headers(options.headers ?? {});
  headers.set('Authorization', `Bearer ${token}`);
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  let response;
  try {
    response = await fetch(`${RENDER_BASE_URL}${path}`, {
      ...options,
      headers,
      signal: controller.signal,
    });
  } catch (cause) {
    if (controller.signal.aborted || cause?.name === 'AbortError') {
      throw new AuthError(
        `No response from the render API within ${timeoutMs}ms.`,
        0,
        { cause },
      );
    }
    throw new AuthError(
      `Cannot reach the orchestrator at ${RENDER_BASE_URL}. It may still be `
      + 'starting up, not deployed yet, or refusing this origin.',
      0,
      { cause },
    );
  } finally {
    window.clearTimeout(timeoutId);
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new AuthError(detailToMessage(payload, response.status), response.status);
  }

  if (response.status === 204) return null;
  return response.json();
}

function detailToMessage(payload, status) {
  const detail = payload?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length) {
    const first = detail[0];
    const field = Array.isArray(first?.loc) ? first.loc[first.loc.length - 1] : null;
    return field ? `${field}: ${first.msg}` : first.msg;
  }
  return `Render API returned ${status}.`;
}

export function createRenderJob(payload) {
  return renderRequest('/render/jobs', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export class RenderUploadError extends Error {
  constructor(message, code, options) {
    super(message, options);
    this.name = 'RenderUploadError';
    this.code = code;
  }
}

// XMLHttpRequest is deliberate here: fetch does not expose browser upload
// progress. Do not add the session Authorization header to this request. The
// destination is object storage on another host and the URL is already signed.
export function uploadRenderSource(uploadUrl, file, {
  expiresAt,
  onProgress,
  signal,
} = {}) {
  return new Promise((resolve, reject) => {
    const expiryMs = expiresAt ? Date.parse(expiresAt) : Number.NaN;
    if (Number.isFinite(expiryMs) && Date.now() >= expiryMs) {
      reject(new RenderUploadError(
        'The signed upload URL expired before the upload could start. The job is still awaiting_upload -- retry to get a fresh URL for the same job.',
        'upload_url_expired',
      ));
      return;
    }

    const xhr = new XMLHttpRequest();
    let settled = false;

    const cleanup = () => {
      signal?.removeEventListener('abort', abortUpload);
    };
    const succeed = () => {
      if (settled) return;
      settled = true;
      cleanup();
      resolve();
    };
    const fail = (error) => {
      if (settled) return;
      settled = true;
      cleanup();
      reject(error);
    };
    const expiredOrRejected = () => {
      const expired = Number.isFinite(expiryMs) && Date.now() >= expiryMs;
      const responseMentionsExpiry = /expired|signature/i.test(xhr.responseText ?? '');
      return expired || responseMentionsExpiry || xhr.status === 401 || xhr.status === 403;
    };
    const uploadFailure = () => {
      if (expiredOrRejected()) {
        return new RenderUploadError(
          'The signed upload URL expired or was rejected by storage. The job is still awaiting_upload -- retry to get a fresh URL for the same job.',
          'upload_url_expired',
        );
      }
      return new RenderUploadError(
        xhr.status
          ? `Object storage rejected the upload (${xhr.status}). The job remains awaiting_upload.`
          : 'The connection to object storage was interrupted. The job remains awaiting_upload and was not submitted.',
        'upload_failed',
      );
    };
    const abortUpload = () => xhr.abort();

    xhr.open('PUT', uploadUrl, true);
    xhr.upload.onprogress = (event) => {
      const total = event.lengthComputable ? event.total : file.size;
      const percent = total > 0 ? Math.min(100, Math.round((event.loaded / total) * 100)) : 0;
      onProgress?.({ loaded: event.loaded, total, percent });
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) succeed();
      else fail(uploadFailure());
    };
    xhr.onerror = () => fail(uploadFailure());
    xhr.onabort = () => fail(new RenderUploadError(
      'The upload was cancelled. The job remains awaiting_upload and was not submitted.',
      'upload_cancelled',
    ));

    if (signal?.aborted) {
      fail(new RenderUploadError('The upload was cancelled.', 'upload_cancelled'));
      return;
    }
    signal?.addEventListener('abort', abortUpload, { once: true });
    xhr.send(file);
  });
}

// A fresh signature for the same object key, for a job still awaiting its
// upload. The presigned PUT is short-lived and a few hundred megabytes over a
// domestic connection is not; without this the job would be stranded and the
// only way forward would be creating a second one, orphaning the first.
export function reissueRenderUploadUrl(jobId) {
  return renderRequest(`/render/jobs/${encodeURIComponent(jobId)}/upload-url`, {
    method: 'POST',
  });
}

export function confirmRenderUpload(jobId) {
  return renderRequest(`/render/jobs/${encodeURIComponent(jobId)}/uploaded`, {
    method: 'POST',
  });
}

export function listRenderJobs() {
  return renderRequest('/render/jobs');
}

export function getRenderJob(jobId) {
  return renderRequest(`/render/jobs/${encodeURIComponent(jobId)}`);
}

export function getRenderArtifacts(jobId) {
  return renderRequest(`/render/jobs/${encodeURIComponent(jobId)}/artifacts`);
}

export function cancelRenderJob(jobId) {
  return renderRequest(`/render/jobs/${encodeURIComponent(jobId)}`, {
    method: 'DELETE',
  });
}
