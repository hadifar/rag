import { api, unwrap } from '@/shared/api/client';
import type { SettingsResponse } from '@/shared/types';

export function fetchSettings(signal?: AbortSignal): Promise<SettingsResponse> {
  return unwrap(api.GET('/api/settings', { signal }));
}
