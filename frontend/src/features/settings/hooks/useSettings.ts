import { useCallback, useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { loadStatus } from '@/shared/api/queryClient';
import type { SettingsResponse } from '@/shared/types';
import { settingsKeys } from '../api/queryKeys';
import { fetchSettings } from '../api/settings';

const EMPTY: SettingsResponse = { model: '', temperature: 0, top_k: 4 };
const SAVED_NOTICE_MS = 3000;

/** The settings form: loaded from the server, edited locally, and saved. */
export function useSettings() {
  const query = useQuery({
    queryKey: settingsKeys.current,
    queryFn: ({ signal }) => fetchSettings(signal),
  });
  // The user's edits; until the first one the form shows the server's values, so a
  // refetch can't overwrite what they typed. A failed load keeps the blank form, so it
  // can still be filled in.
  const [edited, setEdited] = useState<SettingsResponse | null>(null);
  const form = edited ?? query.data ?? EMPTY;
  const [saved, setSaved] = useState(false);

  // Hide the "Saved" notice again after a moment.
  useEffect(() => {
    if (!saved) return;
    const timer = setTimeout(() => setSaved(false), SAVED_NOTICE_MS);
    return () => clearTimeout(timer);
  }, [saved]);

  const update = useCallback(
    <K extends keyof SettingsResponse>(key: K, value: SettingsResponse[K]) => {
      setEdited({ ...form, [key]: value });
    },
    [form]
  );

  // TODO: persist via the settings API once the endpoint supports writes.
  const save = useCallback(() => setSaved(true), []);

  return { form, status: loadStatus(query), saved, update, save };
}
