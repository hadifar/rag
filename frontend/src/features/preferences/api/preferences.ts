import { jsonPostInit, request, requestJson } from '@/shared/api/client';
import type { PreferenceRequest, PreferenceResponse } from '@/shared/types';

/** What the user wants of every answer, oldest first; the chat agent saves to it too. */
export function fetchPreferences(signal?: AbortSignal): Promise<PreferenceResponse[]> {
  return requestJson('settings/preferences', { signal });
}

/** The saved preference; for one the user already has (ignoring case), that one. */
export function addPreference(text: string): Promise<PreferenceResponse> {
  const body: PreferenceRequest = { text };
  return requestJson('settings/preferences', jsonPostInit(body));
}

export async function deletePreference(id: string): Promise<void> {
  await request(`settings/preferences/${encodeURIComponent(id)}`, { method: 'DELETE' });
}
