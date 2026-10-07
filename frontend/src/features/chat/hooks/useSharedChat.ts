import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

import { sharedOn } from '@/features/conversations';
import { errorMessage } from '@/shared/api/errors';
import { loadStatus } from '@/shared/api/queryClient';
import { fetchSharedConversation } from '../api/shares';
import { chatKeys } from '../api/queryKeys';
import { fromHistory } from '../model/transcript';

/** A shared conversation's read-only page: its snapshot, shown as the chat showed it. */
export function useSharedChat(shareId: string) {
  const query = useQuery({
    queryKey: chatKeys.shared(shareId),
    queryFn: ({ signal }) => fetchSharedConversation(shareId, signal),
    // A snapshot only changes when its owner updates the link; a reload shows that.
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });
  const { data } = query;
  const bubbles = useMemo(() => (data ? fromHistory(data.messages).bubbles : []), [data]);

  return {
    status: loadStatus(query),
    title: data?.title ?? null,
    sharedOn: data ? sharedOn(data.shared_at) : null,
    bubbles,
    error: query.isError
      ? errorMessage(
          query.error,
          { 404: 'This link was taken down, or never existed.' },
          "Couldn't load this chat. Please try again."
        )
      : null,
  };
}
