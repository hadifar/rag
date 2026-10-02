import type { UserResponse } from '@/shared/types';

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';

export type AuthContextValue = {
  status: AuthStatus;
  user: UserResponse | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

/** What RequireAuth hands the login page via router state, so it can send the user back
 * to the exact page (including query string) they were redirected from. */
export type LoginRedirectState = { from: string };
