import { useCallback, useEffect, useState } from 'react';
import {
  authenticateProvider,
  clearProviderToken,
  fetchProviderProfile,
  logoutProvider,
  PROVIDER_TOKEN_KEY,
  saveProviderToken,
  storedProviderToken,
} from '../services/providerAuthApi';

export function useProviderSession() {
  const [token, setToken] = useState(storedProviderToken);
  const [profile, setProfile] = useState(null);
  const [revision, setRevision] = useState(0);

  const invalidate = useCallback((rejected) => {
    clearProviderToken(rejected);
    setToken((current) => current === rejected ? null : current);
  }, []);

  useEffect(() => {
    const sync = (event) => {
      if (event.key === PROVIDER_TOKEN_KEY || event.key === null) setToken(storedProviderToken());
    };
    window.addEventListener('storage', sync);
    return () => window.removeEventListener('storage', sync);
  }, []);

  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    fetchProviderProfile(token, controller.signal).then((provider) => {
      if (!controller.signal.aborted) setProfile({ token, revision, provider });
    }).catch((error) => {
      if (controller.signal.aborted) return;
      if (error.status === 401) invalidate(token);
      else setProfile({ token, revision, error: error.message });
    });
    return () => controller.abort();
  }, [token, revision, invalidate]);

  const authenticate = async (mode, fields) => {
    const result = await authenticateProvider(mode, fields);
    saveProviderToken(result.token);
    setToken(result.token);
  };

  const logout = async () => {
    invalidate(token);
    try {
      await logoutProvider(token);
    } catch {
      // The local session is gone. The server session still expires on schedule.
    }
  };

  const verified = profile?.token === token && profile.revision === revision;
  const status = !token ? 'anonymous' : !verified ? 'loading' : profile.error ? 'error' : 'authenticated';
  return {
    status,
    token,
    provider: verified ? profile.provider : null,
    error: verified ? profile.error : null,
    authenticate,
    logout,
    invalidate,
    refresh: () => setRevision((value) => value + 1),
  };
}
