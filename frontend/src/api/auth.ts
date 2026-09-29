import {
  ApiError,
  apiUrl,
  ensureOk,
  jsonPostInit,
  refreshSession,
  requestJson,
  setAccessToken,
} from './client';
import type { LoginRequest, TokenResponse, UserResponse } from '../types';

/**
 * Logs in and stores the access token for every later request. Plain `fetch`, not
 * `authFetch`: a 401 here means wrong credentials, not an expired session to refresh.
 */
export async function login(email: string, password: string): Promise<void> {
  const init: RequestInit = {
    ...jsonPostInit({ email, password } satisfies LoginRequest),
    credentials: 'include',
  };
  const res = ensureOk(await fetch(apiUrl('auth/login'), init), 'auth/login', init);
  const body: TokenResponse = await res.json();
  setAccessToken(body.access_token);
}

/** Restores a session from the refresh cookie, e.g. on page load. */
export async function restoreSession(): Promise<void> {
  if (!(await refreshSession())) {
    throw new ApiError(401, 'no session to restore');
  }
}

/**
 * Clears the local session unconditionally, then best-effort tells the server so the
 * refresh cookie is deleted too. Never throws: an offline/flaky network shouldn't leave
 * the UI stuck showing the user as still logged in.
 */
export async function logout(): Promise<void> {
  setAccessToken(null);
  try {
    await fetch(apiUrl('auth/logout'), { method: 'POST', credentials: 'include' });
  } catch {
    // Best effort — the local session is already cleared regardless.
  }
}

export function me(): Promise<UserResponse> {
  return requestJson('auth/me');
}
