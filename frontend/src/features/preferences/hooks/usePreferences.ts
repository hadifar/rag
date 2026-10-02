import { useCallback, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { ApiError } from '@/shared/api/client';
import { loadStatus } from '@/shared/api/queryClient';
import type { PreferenceResponse } from '@/shared/types';
import { addPreference, deletePreference, fetchPreferences } from '../api/preferences';
import { preferenceKeys } from '../api/queryKeys';
import { addPreferenceError, withPreference } from '../model/preferences';

async function deleteIfPresent(id: string): Promise<void> {
  try {
    await deletePreference(id);
  } catch (e) {
    // A 404: already gone, e.g. the assistant forgot it in a chat since the page loaded.
    if (!(e instanceof ApiError && e.status === 404)) throw e;
  }
}

/**
 * The user's answer preferences, added to and removed from here. The chat agent saves to
 * them too, so they're reloaded each time the page opens.
 */
export function usePreferences() {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: preferenceKeys.list,
    queryFn: ({ signal }) => fetchPreferences(signal),
  });
  const [draft, setDraft] = useState('');
  const [error, setError] = useState<string | null>(null);

  const updateList = useCallback(
    (update: (list: PreferenceResponse[]) => PreferenceResponse[]) => {
      queryClient.setQueryData<PreferenceResponse[]>(preferenceKeys.list, (list) =>
        list ? update(list) : list
      );
    },
    [queryClient]
  );

  const adding = useMutation({
    mutationFn: addPreference,
    onMutate: () => setError(null),
    onSuccess: (saved) => {
      updateList((list) => withPreference(list, saved));
      setDraft('');
    },
    onError: (e) => setError(addPreferenceError(e instanceof ApiError ? e.status : null)),
  });

  const removing = useMutation({
    mutationFn: deleteIfPresent,
    onMutate: () => setError(null),
    onSuccess: (_, id) => updateList((list) => list.filter((p) => p.id !== id)),
    onError: () => setError("Couldn't remove the preference; try again."),
  });

  const text = draft.trim();
  const { mutate: addText } = adding;
  const { mutate: removeId } = removing;

  const add = useCallback(() => {
    if (text) addText(text);
  }, [text, addText]);

  const remove = useCallback((id: string) => removeId(id), [removeId]);

  return {
    preferences: query.data ?? [],
    status: loadStatus(query),
    draft,
    setDraft,
    canAdd: text.length > 0 && !adding.isPending,
    error,
    add,
    remove,
  };
}
