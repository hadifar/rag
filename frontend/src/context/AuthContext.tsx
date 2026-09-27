import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import { login as apiLogin, logout as apiLogout, me, refresh } from '../api/auth';
import type { Schemas } from '../types';

type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';

type AuthContextValue = {
  status: AuthStatus;
  user: Schemas['UserResponse'] | null;
  accessToken: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [user, setUser] = useState<Schemas['UserResponse'] | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);

  const applySession = useCallback(async (token: string) => {
    const currentUser = await me(token);
    setAccessToken(token);
    setUser(currentUser);
    setStatus('authenticated');
  }, []);

  useEffect(() => {
    refresh()
      .then((tokenResponse) => applySession(tokenResponse.access_token))
      .catch(() => {
        setAccessToken(null);
        setUser(null);
        setStatus('unauthenticated');
      });
  }, [applySession]);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokenResponse = await apiLogin(email, password);
      await applySession(tokenResponse.access_token);
    },
    [applySession]
  );

  const logout = useCallback(async () => {
    await apiLogout();
    setAccessToken(null);
    setUser(null);
    setStatus('unauthenticated');
  }, []);

  const value = useMemo(
    () => ({ status, user, accessToken, login, logout }),
    [status, user, accessToken, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
