import { apiUrl } from './base';
import type { Settings } from '../types';

export async function fetchSettings(): Promise<Settings> {
  const res = await fetch(apiUrl('settings'));
  if (!res.ok) {
    throw new Error(`failed to load settings: ${res.status}`);
  }
  return res.json();
}
