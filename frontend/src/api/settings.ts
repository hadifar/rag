import { requestJson } from './client';
import type { Schemas } from '../types';

export function fetchSettings(): Promise<Schemas['SettingsResponse']> {
  return requestJson('settings');
}
