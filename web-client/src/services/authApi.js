// Accounts: login, logout, and the session token that ties them
// together.
//
// Two things live here that could have been split, and are not on purpose.
//
// The token store is in this file rather than in a hook, because the API client
// needs it too. `inferenceApi.js` sends the session token when administering
// keys, and it must read the same value the login flow wrote -- a token cached
// in React state would leave those two disagreeing the moment a component
// unmounted.
//
// Errors are thrown as `AuthError` carrying the HTTP status. The status is the
// whole point: 401 on /me means "log in again", 401 on login means "wrong
// password", and 503 means the backend is up but its database is not. Collapsing
// those into a string would make the caller parse English to decide what to do.

import { ORCHESTRATOR_URL } from './api';

export const AUTH_BASE_URL = `${ORCHESTRATOR_URL}/v1/auth`;

// localStorage, not a cookie. The orchestrator authenticates with a Bearer
// header, so there is nothing for a cookie to do -- and a token the browser
// attaches automatically to every request is the ingredient CSRF needs. A header
// the code sets deliberately cannot be sent by another origin's form.
//
// The tradeoff, stated rather than hidden: localStorage is readable by any
// script on this origin, so an XSS bug leaks the session. That is a real cost.
// It is the right trade only while the alternative would be a cookie without
// SameSite and CSRF protection, which is where this would otherwise land.
const TOKEN_KEY = 'nodeforge.session';

export class AuthError extends Error {
  // `options` is forwarded to Error so `cause` survives. Callers pass the
  // original TypeError from fetch, and dropping it -- as this constructor did
  // when it took only two parameters -- discards the one piece of information
  // that says whether the request was refused, blocked, or never sent. The
  // extra argument was silently ignored, which is the failure mode this
  // codebase keeps chasing: no error, just missing detail at the moment it
  // matters.
  constructor(message, status, options) {
    super(message, options);
    this.name = 'AuthError';
    this.status = status;
  }
}

// Every read is wrapped. Safari in private mode throws on localStorage access
// rather than returning null, and an unhandled throw here would blank the whole
// app on load -- before any error boundary exists to catch it.
export function storedToken() {
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function storeToken(token) {
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
  } catch {
    // Non-fatal. The session still works for this tab via the value the caller
    // is holding; it simply will not survive a reload. Failing the login over
    // it would be worse.
  }
}

export function clearToken() {
  try {
    window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* nothing useful to do */
  }
}

export async function authRequest(
  path,
  { method = 'POST', body, token, baseUrl = AUTH_BASE_URL, signal } = {},
) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (cause) {
    // fetch rejects with an identical TypeError for a host that is not there
    // and for a response the browser refused on CORS grounds -- the spec hides
    // which, deliberately, so that a page cannot probe another origin by
    // watching its own errors. Three very different problems arrive here
    // indistinguishable, so the message names all three rather than asserting
    // the one that happens to be most common.
    throw new AuthError(
      `Cannot reach the orchestrator at ${baseUrl}. It may still be `
      + `starting up (a free-tier backend can take ~50s to wake), not deployed `
      + `yet, or refusing this origin. Check the browser console for the `
      + `specific reason.`,
      0,
      { cause },
    );
  }

  if (response.status === 204) return null;

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new AuthError(detailToMessage(payload, response.status), response.status);
  }
  return payload;
}

// FastAPI returns `detail` as a string for HTTPException and as an array of
// per-field objects for a 422. Rendering the array straight into JSX prints
// "[object Object]", which is how a validation message becomes useless at
// exactly the moment someone needs it.
function detailToMessage(payload, status) {
  const detail = payload?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length) {
    const first = detail[0];
    const field = Array.isArray(first?.loc) ? first.loc[first.loc.length - 1] : null;
    return field ? `${field}: ${first.msg}` : first.msg;
  }
  return `Request failed (${status}).`;
}

export async function login({ email, password }) {
  const session = await authRequest('/login', { body: { email, password } });
  storeToken(session.token);
  return session;
}

export async function logout() {
  const token = storedToken();
  // Clear locally first, and unconditionally. If the request fails the user
  // still expects to be logged out of this browser, and leaving the token in
  // place because the network blipped is the surprising outcome. The server-side
  // session then expires on its own.
  clearToken();
  if (!token) return;
  try {
    await authRequest('/logout', { token });
  } catch {
    /* already cleared locally; nothing left to do */
  }
}

export async function fetchCurrentUser(token = storedToken()) {
  if (!token) return null;
  try {
    return await authRequest('/me', { method: 'GET', token });
  } catch (error) {
    // 401 means the token is expired or revoked -- a normal end of a session,
    // not an error to show anybody. Drop it so the app renders logged-out.
    // Anything else (503, network) is a real failure and must propagate, or a
    // database outage would silently look like being signed out.
    if (error.status === 401) {
      clearToken();
      return null;
    }
    throw error;
  }
}
