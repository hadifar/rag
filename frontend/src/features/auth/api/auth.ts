import {
  ApiError,
  api,
  apiError,
  apiUrl,
  jsonPostInit,
  refreshSession,
  setAccessToken,
  unwrap,
} from '@/shared/api/client';
import type { LoginRequest, TokenResponse, UserResponse } from '@/shared/types';

/**
 * Logs in and stores the access token for every later request. Plain `fetch`, not
 * `authFetch`: a 401 here means wrong credentials, not an expired session to refresh.
 */
export async function login(email: string, password: string): Promise<void> {
  const res = await fetch(apiUrl('auth/login'), {
    ...jsonPostInit({ email, password } satisfies LoginRequest),
    credentials: 'include',
  });
  if (!res.ok) throw await apiError(res, 'POST /api/auth/login');
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
  return unwrap(api.GET('/api/auth/me'));
}
