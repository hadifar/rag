import { useCallback, useEffect, useState } from 'react';

import { useLoadOnMount } from '@/shared/hooks/useLoadOnMount';
import type { LoadStatus, SettingsResponse } from '@/shared/types';
import { fetchSettings } from '../api/settings';

const EMPTY: SettingsResponse = { model: '', temperature: 0, top_k: 4 };
const SAVED_NOTICE_MS = 3000;

/** The settings form: loaded from the server, edited locally, and saved. */
export function useSettings() {
  const [form, setForm] = useState<SettingsResponse>(EMPTY);
  const [status, setStatus] = useState<LoadStatus>('loading');
  const [saved, setSaved] = useState(false);

  useLoadOnMount(
    fetchSettings,
    (settings) => {
      setForm(settings);
      setStatus('ready');
    },
    () => setStatus('error') // keeps the blank form, so it can still be filled in
  );

  // Hide the "Saved" notice again after a moment.
  useEffect(() => {
    if (!saved) return;
    const timer = setTimeout(() => setSaved(false), SAVED_NOTICE_MS);
    return () => clearTimeout(timer);
  }, [saved]);

  const update = useCallback(
    <K extends keyof SettingsResponse>(key: K, value: SettingsResponse[K]) => {
      setForm((current) => ({ ...current, [key]: value }));
    },
    []
  );

  // TODO: persist via the settings API once the endpoint supports writes.
  const save = useCallback(() => setSaved(true), []);

  return { form, status, saved, update, save };
}
