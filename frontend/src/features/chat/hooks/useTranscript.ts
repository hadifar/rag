import { useEffect, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';

import { fetchConversationMessages } from '@/features/conversations';
import { ApiError } from '@/shared/api/client';
import { chatKeys } from '../api/queryKeys';
import { emptyTranscript, errorTranscript, fromHistory } from '../model/transcript';
import type { Transcript } from '../types';

function historyErrorText(err: unknown): string {
  return err instanceof ApiError && err.status === 404
    ? "This conversation doesn't exist or was deleted."
    : "Couldn't load this conversation. Please try again.";
}

/**
 * The conversation on screen: its saved history, loaded on opening it, plus whatever
 * `useSendMessage` streams into the same cache entry. `undefined` is a new chat.
 */
export function useTranscript(conversationId: string | undefined): Transcript {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: chatKeys.transcript(conversationId),
    queryFn: async ({ signal }) =>
      fromHistory(await fetchConversationMessages(conversationId!, signal)),
    enabled: conversationId !== undefined,
    // Once loaded, the stream keeps it current: a refetch mid-answer would replace it.
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });

  // Leaving a conversation drops what was shown, so opening it again loads it from the
  // server. A reset keeps the cache entry itself, which an observer may still hold.
  useEffect(
    () => () => void queryClient.resetQueries({ queryKey: chatKeys.transcript(conversationId), exact: true }),
    [queryClient, conversationId]
  );

  const { data, error } = query;
  return useMemo(() => data ?? (error ? errorTranscript(historyErrorText(error)) : EMPTY), [data, error]);
}

const EMPTY = emptyTranscript();
