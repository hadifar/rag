import { useCallback } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';

import { loadStatus } from '@/shared/api/queryClient';
import { listConversations } from '../api/conversations';
import { conversationKeys } from '../api/queryKeys';
import { flattenPages } from '../model/conversations';

/** The user's conversations, most recently used first, a page at a time. */
export function useConversationList() {
  const query = useInfiniteQuery({
    queryKey: conversationKeys.list,
    queryFn: ({ pageParam, signal }) => listConversations(pageParam, signal),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
    select: flattenPages,
  });
  const { hasNextPage, isFetchingNextPage, fetchNextPage } = query;

  // A failed page just leaves the button enabled, so the user can try again.
  const loadMore = useCallback(() => {
    if (hasNextPage && !isFetchingNextPage) void fetchNextPage();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  return {
    conversations: query.data ?? [],
    status: loadStatus(query),
    hasMore: hasNextPage,
    isLoadingMore: isFetchingNextPage,
    loadMore,
  };
}
