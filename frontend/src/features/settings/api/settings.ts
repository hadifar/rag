import { api, unwrap } from '@/shared/api/client';
import type { SettingsResponse } from '@/shared/types';

/** The app's settings, as the backend is configured. */
export function fetchSettings(signal?: AbortSignal): Promise<SettingsResponse> {
  return unwrap(api.GET('/api/settings', { signal }));
}
