import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import { login as apiLogin, logout as apiLogout, me, restoreSession } from '../api/auth';
import { onSessionExpired } from '../api/client';
import type { AuthStatus, UserResponse } from '../types';
import { AuthContext } from '../hooks/useAuth';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [user, setUser] = useState<UserResponse | null>(null);

  const applySession = useCallback(async () => {
    setUser(await me());
    setStatus('authenticated');
  }, []);

  const clearSession = useCallback(() => {
    setUser(null);
    setStatus('unauthenticated');
  }, []);

  useEffect(() => {
    restoreSession().then(applySession).catch(clearSession);
  }, [applySession, clearSession]);

  // A request's 401 couldn't be fixed by refreshing: RequireAuth sends the user to /login.
  useEffect(() => onSessionExpired(clearSession), [clearSession]);

  const login = useCallback(
    async (email: string, password: string) => {
      await apiLogin(email, password);
      await applySession();
    },
    [applySession]
  );

  const logout = useCallback(async () => {
    await apiLogout();
    clearSession();
  }, [clearSession]);

  const value = useMemo(
    () => ({ status, user, login, logout }),
    [status, user, login, logout]
  );

  return <AuthContext value={value}>{children}</AuthContext>;
}
