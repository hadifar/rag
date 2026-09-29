import { requestJson } from './client';
import type { SettingsResponse } from '../types';

export function fetchSettings(): Promise<SettingsResponse> {
  return requestJson('settings');
}
