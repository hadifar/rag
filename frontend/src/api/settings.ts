import { apiUrl, authHeader } from './base';
import type { Schemas } from '../types';

export async function fetchSettings(
  accessToken: string
): Promise<Schemas['SettingsResponse']> {
  const res = await fetch(apiUrl('settings'), { headers: authHeader(accessToken) });
  if (!res.ok) {
    throw new Error(`failed to load settings: ${res.status}`);
  }
  return res.json();
}
