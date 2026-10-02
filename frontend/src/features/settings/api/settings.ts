import { requestJson } from '@/shared/api/client';
import type { SettingsResponse } from '@/shared/types';

export function fetchSettings(signal?: AbortSignal): Promise<SettingsResponse> {
  return requestJson('settings', { signal });
}
