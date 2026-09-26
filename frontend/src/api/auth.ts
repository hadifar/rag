import { apiUrl, jsonPost } from './base';
import type { Schemas } from '../types';

export class AuthError extends Error {}

async function parseTokenResponse(res: Response): Promise<Schemas['TokenResponse']> {
  if (!res.ok) {
    throw new AuthError(`request failed: ${res.status}`);
  }
  return res.json();
}

export function login(
  email: string,
  password: string
): Promise<Schemas['TokenResponse']> {
  return fetch(apiUrl('auth/login'), {
    ...jsonPost({ email, password } satisfies Schemas['LoginRequest']),
    credentials: 'include',
  }).then(parseTokenResponse);
}

export function refresh(): Promise<Schemas['TokenResponse']> {
  return fetch(apiUrl('auth/refresh'), {
    method: 'POST',
    credentials: 'include',
  }).then(parseTokenResponse);
}

export async function logout(): Promise<void> {
  await fetch(apiUrl('auth/logout'), { method: 'POST', credentials: 'include' });
}

export async function me(accessToken: string): Promise<Schemas['UserResponse']> {
  const res = await fetch(apiUrl('auth/me'), {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) {
    throw new AuthError(`request failed: ${res.status}`);
  }
  return res.json();
}
