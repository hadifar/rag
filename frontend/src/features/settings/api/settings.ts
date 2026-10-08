import { api, unwrap } from '@/shared/api/client';
import type { RunSettingsResponse, RunSettingsUpdateRequest, SettingsResponse } from '@/shared/types';

/** The app's settings, as the backend is configured. */
export function fetchSettings(signal?: AbortSignal): Promise<SettingsResponse> {
  return unwrap(api.GET('/api/settings', { signal }));
}

/** The model and effort the user's turns run on, in every conversation. */
export function fetchRunSettings(signal?: AbortSignal): Promise<RunSettingsResponse> {
  return unwrap(api.GET('/api/settings/me', { signal }));
}

/** Sets the model or effort the user's turns run on; a field left out stays as is. */
export function updateRunSettings(body: RunSettingsUpdateRequest): Promise<RunSettingsResponse> {
  return unwrap(api.PATCH('/api/settings/me', { body }));
}
