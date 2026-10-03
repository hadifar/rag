import type { PreferenceResponse } from '@/shared/types';

// PreferenceRequest's max_length in rag/api/schema/setting.py.
export const MAX_PREFERENCE_LENGTH = 200;

/** `list` with `preference` added at the end, unless it's already there (a duplicate comes back as the saved one). */
export function withPreference(
  list: PreferenceResponse[],
  preference: PreferenceResponse
): PreferenceResponse[] {
  return list.some((p) => p.id === preference.id) ? list : [...list, preference];
}

/** What to tell the user when adding a preference failed: by the response's status, or null if there was none. */
export function addPreferenceError(status: number | null): string {
  if (status === 409) {
    return 'You have as many preferences as you can keep; remove one first.';
  }
  if (status === 400 || status === 422) {
    return `A preference needs some text, up to ${MAX_PREFERENCE_LENGTH} characters.`;
  }
  return "Couldn't save the preference; try again.";
}
