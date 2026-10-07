import { useCallback, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import type { ConversationResponse } from '@/shared/types';
import { conversationKeys } from '../api/queryKeys';
import {
  hasMorePages,
  moveToTop,
  patchPages,
  placeByRecency,
  removeConversation,
  renameConversation,
  replaceOrPrepend,
  upsertConversation,
  type ConversationPages,
} from '../model/conversations';

type Update = (list: ConversationResponse[]) => ConversationResponse[];

/**
 * Keeps the cached lists (the recent ones and the pinned ones) in step with what the
 * user just did, without refetching them. A change before a list has loaded is
 * skipped: the load brings it anyway.
 */
export function useConversationCache() {
  const queryClient = useQueryClient();

  const patchRecent = useCallback(
    (update: (list: ConversationResponse[], hasMore: boolean) => ConversationResponse[]) => {
      queryClient.setQueryData<ConversationPages>(conversationKeys.list, (data) =>
        data ? patchPages(data, (list) => update(list, hasMorePages(data))) : data
      );
    },
    [queryClient]
  );

  const patchPinned = useCallback(
    (update: Update) => {
      queryClient.setQueryData<ConversationResponse[]>(conversationKeys.pinned, (list) =>
        list ? update(list) : list
      );
    },
    [queryClient]
  );

  const patchBoth = useCallback(
    (update: Update) => {
      patchRecent(update);
      patchPinned(update);
    },
    [patchRecent, patchPinned]
  );

  return useMemo(
    () => ({
      /** Add `conversation` at the top of the recent ones, or move it there. */
      upsert: (conversation: ConversationResponse) =>
        patchRecent((list) => upsertConversation(list, conversation)),
      /** A message was sent to the conversation with `id`: move it to the top (unless pinned). */
      bump: (id: string) => patchRecent((list) => moveToTop(list, id)),
      rename: (id: string, title: string) =>
        patchBoth((list) => renameConversation(list, id, title)),
      remove: (id: string) => patchBoth((list) => removeConversation(list, id)),
      /** The server changed `conversation` (renamed, pinned or unpinned): show it in its list. */
      place: (conversation: ConversationResponse) => {
        const without: Update = (list) => removeConversation(list, conversation.id);
        if (conversation.pinned_at) {
          patchRecent(without);
          patchPinned((list) => replaceOrPrepend(list, conversation));
        } else {
          patchPinned(without);
          patchRecent((list, hasMore) => placeByRecency(list, conversation, hasMore));
        }
      },
    }),
    [patchRecent, patchPinned, patchBoth]
  );
}
