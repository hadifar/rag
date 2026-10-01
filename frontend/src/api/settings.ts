import { jsonPostInit, request, requestJson } from './client';
import type { PreferenceRequest, PreferenceResponse, SettingsResponse } from '../types';

export function fetchSettings(signal?: AbortSignal): Promise<SettingsResponse> {
  return requestJson('settings', { signal });
}

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
