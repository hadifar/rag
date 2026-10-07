import { useQuery } from '@tanstack/react-query';

import { loadStatus } from '@/shared/api/queryClient';
import { listPinnedConversations } from '../api/conversations';
import { conversationKeys } from '../api/queryKeys';

/** The user's pinned conversations, last pinned first; all of them, as there are few. */
export function usePinnedConversations() {
  const query = useQuery({
    queryKey: conversationKeys.pinned,
    queryFn: ({ signal }) => listPinnedConversations(signal),
  });

  return { pinned: query.data ?? [], status: loadStatus(query) };
}
