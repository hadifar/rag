import { requestJson } from './client';
import type { SettingsResponse } from '../types';

export function fetchSettings(signal?: AbortSignal): Promise<SettingsResponse> {
  return requestJson('settings', { signal });
}
