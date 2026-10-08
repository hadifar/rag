import { useCallback } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { fetchRunSettings, settingsKeys, updateRunSettings } from '@/features/settings';
import { DEFAULT_RUN_SETTINGS } from '../model/runSettings';
import type { Effort, ModelName, RunSettings } from '../types';

/**
 * The model and effort the user's turns run on, and changing them. They're the user's,
 * not a conversation's: a pick made in one conversation carries over to every other,
 * new or old. The defaults show until the user's load.
 */
export function useRunSettings() {
  const queryClient = useQueryClient();
  const key = settingsKeys.runSettings;
  const { data } = useQuery({ queryKey: key, queryFn: ({ signal }) => fetchRunSettings(signal) });
  const settings: RunSettings = data ?? DEFAULT_RUN_SETTINGS;

  const { mutate } = useMutation({
    mutationFn: updateRunSettings,
    // Shown at once; put back if the server refuses it.
    onMutate: (change: Partial<RunSettings>) => {
      const previous = queryClient.getQueryData<RunSettings>(key);
      queryClient.setQueryData<RunSettings>(key, { ...DEFAULT_RUN_SETTINGS, ...previous, ...change });
      return { previous };
    },
    onError: (_err, _change, context) => queryClient.setQueryData(key, context?.previous),
    onSuccess: (saved) => queryClient.setQueryData(key, saved),
  });

  return {
    settings,
    setModel: useCallback((model: ModelName) => mutate({ model }), [mutate]),
    setEffort: useCallback((effort: Effort) => mutate({ effort }), [mutate]),
  };
}
