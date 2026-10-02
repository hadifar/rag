import { useCallback, useState } from 'react';

import { ApiError } from '@/shared/api/client';
import { useLoadOnMount } from '@/shared/hooks/useLoadOnMount';
import type { LoadStatus, PreferenceResponse } from '@/shared/types';
import { addPreference, deletePreference, fetchPreferences } from '../api/preferences';
import { addPreferenceError, withPreference } from '../model/preferences';

/** The user's answer preferences: loaded when the page opens, added to and removed from here. */
export function usePreferences() {
  const [preferences, setPreferences] = useState<PreferenceResponse[]>([]);
  const [status, setStatus] = useState<LoadStatus>('loading');
  const [draft, setDraft] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useLoadOnMount(
    fetchPreferences,
    (loaded) => {
      setPreferences(loaded);
      setStatus('ready');
    },
    () => setStatus('error')
  );

  const text = draft.trim();

  const add = useCallback(async () => {
    if (!text) return;
    setSaving(true);
    setError(null);
    try {
      const saved = await addPreference(text);
      setPreferences((current) => withPreference(current, saved));
      setDraft('');
    } catch (e) {
      setError(addPreferenceError(e instanceof ApiError ? e.status : null));
    } finally {
      setSaving(false);
    }
  }, [text]);

  const remove = useCallback(async (id: string) => {
    setError(null);
    try {
      await deletePreference(id);
    } catch (e) {
      // A 404: already gone, e.g. the assistant forgot it in a chat since the page loaded.
      if (!(e instanceof ApiError && e.status === 404)) {
        setError("Couldn't remove the preference; try again.");
        return;
      }
    }
    setPreferences((current) => current.filter((p) => p.id !== id));
  }, []);

  return {
    preferences,
    status,
    draft,
    setDraft,
    canAdd: text.length > 0 && !saving,
    error,
    add,
    remove,
  };
}
