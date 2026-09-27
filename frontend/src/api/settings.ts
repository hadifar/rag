import { apiUrl, authFetch } from './client';
import type { Schemas } from '../types';

export async function fetchSettings(): Promise<Schemas['SettingsResponse']> {
  const res = await authFetch(apiUrl('settings'));
  if (!res.ok) {
    throw new Error(`failed to load settings: ${res.status}`);
  }
  return res.json();
}
