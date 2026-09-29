import type { UserResponse } from './api';

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';

export type AuthContextValue = {
  status: AuthStatus;
  user: UserResponse | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};
