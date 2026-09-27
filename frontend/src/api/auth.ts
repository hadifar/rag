import { apiUrl, authFetch, jsonPostInit, refreshSession, setAccessToken } from './client';
import type { Schemas } from '../types';

export class AuthError extends Error {}

/** Logs in and stores the access token for every later request. */
export async function login(email: string, password: string): Promise<void> {
  const res = await fetch(apiUrl('auth/login'), {
    ...jsonPostInit({ email, password } satisfies Schemas['LoginRequest']),
    credentials: 'include',
  });
  if (!res.ok) {
    throw new AuthError(`request failed: ${res.status}`);
  }
  const body: Schemas['TokenResponse'] = await res.json();
  setAccessToken(body.access_token);
}

/** Restores a session from the refresh cookie, e.g. on page load. */
export async function restoreSession(): Promise<void> {
  if (!(await refreshSession())) {
    throw new AuthError('no session to restore');
  }
}

export async function logout(): Promise<void> {
  setAccessToken(null);
  await fetch(apiUrl('auth/logout'), { method: 'POST', credentials: 'include' });
}

export async function me(): Promise<Schemas['UserResponse']> {
  const res = await authFetch(apiUrl('auth/me'));
  if (!res.ok) {
    throw new AuthError(`request failed: ${res.status}`);
  }
  return res.json();
}
