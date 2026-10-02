import { useCallback, useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { ReactNode } from 'react';

import { login as apiLogin, logout as apiLogout, me, restoreSession } from '../api/auth';
import { onSessionExpired, setAccessToken } from '@/shared/api/client';
import type { UserResponse } from '@/shared/types';
import type { AuthStatus } from '../types';
import { AuthContext } from '../hooks/useAuth';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [user, setUser] = useState<UserResponse | null>(null);
  const queryClient = useQueryClient();

  const applySession = useCallback(async () => {
    setUser(await me());
    setStatus('authenticated');
  }, []);

  const clearSession = useCallback(() => {
    // A successful refresh followed by a failing `me()` (transient 500, flaky network)
    // must not leave an in-memory token behind once we report the user as logged out.
    setAccessToken(null);
    // Cached server data is the old user's: the next one to sign in mustn't see it.
    queryClient.clear();
    setUser(null);
    setStatus('unauthenticated');
  }, [queryClient]);

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
