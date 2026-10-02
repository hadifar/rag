import { api, unwrap } from '@/shared/api/client';
import type { PreferenceResponse } from '@/shared/types';

/** What the user wants of every answer, oldest first; the chat agent saves to it too. */
export function fetchPreferences(signal?: AbortSignal): Promise<PreferenceResponse[]> {
  return unwrap(api.GET('/api/settings/preferences', { signal }));
}

/** The saved preference; for one the user already has (ignoring case), that one. */
export function addPreference(text: string): Promise<PreferenceResponse> {
  return unwrap(api.POST('/api/settings/preferences', { body: { text } }));
}

export async function deletePreference(id: string): Promise<void> {
  await unwrap(
    api.DELETE('/api/settings/preferences/{preference_id}', { params: { path: { preference_id: id } } })
  );
}
