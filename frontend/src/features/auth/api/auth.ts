import {
  ApiError,
  api,
  publicApi,
  refreshSession,
  setAccessToken,
  unwrap,
} from '@/shared/api/client';
import type { UserResponse } from '@/shared/types';

/**
 * Logs in and stores the access token for every later request. Through `publicApi`:
 * a 401 here means wrong credentials, not an expired session to refresh.
 */
export async function login(email: string, password: string): Promise<void> {
  const { access_token } = await unwrap(
    publicApi.POST('/api/auth/login', { body: { email, password } })
  );
  setAccessToken(access_token);
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
    await publicApi.POST('/api/auth/logout');
  } catch {
    // Best effort — the local session is already cleared regardless.
  }
}

export function me(): Promise<UserResponse> {
  return unwrap(api.GET('/api/auth/me'));
}
