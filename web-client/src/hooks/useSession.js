// Who is signed in, shared by every surface that needs to know.
//
// Extracted for the same reason as useProviderNodes: two places need the same
// answer and must never disagree about it. The app shell decides whether to
// render a dashboard or bounce to login; the models page decides whether it can
// list keys. Two independent checks would drift, and the visible symptom would
// be a dashboard that renders for a moment and then throws a 401 -- which reads
// as "this site is broken" rather than "you are signed out".
//
// `status` is a state machine, not a boolean, for the reason `api.js` gives
// about node lists: "loading" and "error" are distinct from "signed out", and
// treating a failed request as signed-out would log people out every time the
// database hiccups.

import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import {
  clearToken,
  fetchCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
  signup as signupRequest,
  storedToken,
} from '../services/authApi';

function useSessionState() {
  const [state, setState] = useState({
    // 'loading' until the stored token has actually been checked against the
    // server. Starting at 'anonymous' would flash the login page for anyone who
    // is already signed in, on every single page load.
    status: storedToken() ? 'loading' : 'anonymous',
    user: null,
    error: null,
  });

  const verify = useCallback(async () => {
    const token = storedToken();
    if (!token) {
      setState({ status: 'anonymous', user: null, error: null });
      return;
    }
    try {
      const user = await fetchCurrentUser(token);
      setState(
        user
          ? { status: 'authenticated', user, error: null }
          : { status: 'anonymous', user: null, error: null },
      );
    } catch (error) {
      // Reached only for non-401 failures -- fetchCurrentUser turns 401 into
      // null. So this is the backend being unreachable or degraded, and the
      // user's session may well be fine. Say so instead of signing them out.
      setState({ status: 'error', user: null, error: error.message });
    }
  }, []);

  useEffect(() => {
    verify();
  }, [verify]);

  // A token written in another tab -- signing in twice, or signing out -- should
  // not leave this tab showing the wrong person. The storage event fires only in
  // *other* tabs, so this cannot loop on its own writes.
  useEffect(() => {
    const onStorage = (event) => {
      if (event.key === 'nodeforge.session') verify();
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, [verify]);

  const signup = useCallback(async (fields) => {
    const session = await signupRequest(fields);
    setState({ status: 'authenticated', user: session.user, error: null });
    return session;
  }, []);

  const login = useCallback(async (fields) => {
    const session = await loginRequest(fields);
    setState({ status: 'authenticated', user: session.user, error: null });
    return session;
  }, []);

  const logout = useCallback(async () => {
    await logoutRequest();
    setState({ status: 'anonymous', user: null, error: null });
  }, []);

  // For a 401 arriving from somewhere other than the auth endpoints -- a key
  // listing, say. The session died mid-visit and every surface needs to agree
  // about that immediately, not on the next reload.
  const invalidate = useCallback(() => {
    clearToken();
    setState({ status: 'anonymous', user: null, error: null });
  }, []);

  return { ...state, signup, login, logout, invalidate, refresh: verify };
}


// One session for the whole app.
//
// `useSessionState` above is the implementation; nothing outside this file
// should call it directly. Calling it twice creates two independent sessions
// that each fetch /me and each hold their own copy of the answer -- so
// invalidating one would leave the other still rendering a signed-in dashboard.
// That is the exact "two surfaces disagreeing" failure this file's header warns
// about, and it is easy to reintroduce by accident, which is why the hook is no
// longer exported under a tempting name.
const SessionContext = createContext(null);

export function SessionProvider({ children }) {
  const value = useSessionState();
  return React.createElement(SessionContext.Provider, { value }, children);
}

export function useSession() {
  const value = useContext(SessionContext);
  if (!value) {
    // A component rendered outside the provider would otherwise read `null` and
    // fail later with "cannot read status of null", pointing at the consumer
    // rather than at the missing provider.
    throw new Error('useSession must be used inside <SessionProvider>');
  }
  return value;
}
