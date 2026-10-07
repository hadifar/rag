import { useCallback, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { fetchConversation, updateConversation } from '@/features/conversations';
import type { ConversationResponse } from '@/shared/types';
import { chatKeys } from '../api/queryKeys';
import { DEFAULT_RUN_SETTINGS } from '../model/runSettings';
import type { Effort, ModelName, RunSettings } from '../types';

type Change = { id: string; change: Partial<RunSettings> };

/**
 * The model and effort the conversation on screen runs on, and changing them. An
 * existing conversation keeps them on the server; a new chat holds the user's pick
 * until its first message creates it (see `useSendMessage`). The last pick also starts
 * the next new chat.
 */
export function useRunSettings(conversationId: string | undefined) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<RunSettings>(DEFAULT_RUN_SETTINGS);
  const query = useQuery({
    queryKey: chatKeys.conversation(conversationId ?? ''),
    queryFn: ({ signal }) => fetchConversation(conversationId!, signal),
    enabled: conversationId !== undefined,
  });
  const saved = conversationId !== undefined ? query.data : undefined;
  const settings: RunSettings = saved ? { model: saved.model, effort: saved.effort } : draft;

  const { mutate } = useMutation({
    mutationFn: ({ id, change }: Change) => updateConversation(id, change),
    // Shown at once; put back if the server refuses it.
    onMutate: ({ id, change }: Change) => {
      const key = chatKeys.conversation(id);
      const previous = queryClient.getQueryData<ConversationResponse>(key);
      if (previous) queryClient.setQueryData(key, { ...previous, ...change });
      return { previous };
    },
    onError: (_err, { id }, context) => {
      if (context?.previous) queryClient.setQueryData(chatKeys.conversation(id), context.previous);
    },
    onSuccess: (conversation) => queryClient.setQueryData(chatKeys.conversation(conversation.id), conversation),
  });

  const change = useCallback(
    (update: Partial<RunSettings>) => {
      setDraft((d) => ({ ...d, ...update }));
      if (conversationId !== undefined) mutate({ id: conversationId, change: update });
    },
    [conversationId, mutate]
  );

  return {
    settings,
    setModel: useCallback((model: ModelName) => change({ model }), [change]),
    setEffort: useCallback((effort: Effort) => change({ effort }), [change]),
  };
}
