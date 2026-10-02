import { useCallback, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import type { ConversationResponse } from '@/shared/types';
import { conversationKeys } from '../api/queryKeys';
import {
  moveToTop,
  patchPages,
  removeConversation,
  renameConversation,
  upsertConversation,
  type ConversationPages,
} from '../model/conversations';

/**
 * Keeps the cached list in step with what the user just did, without refetching it.
 * A change before the list has loaded is skipped: the load brings it anyway.
 */
export function useConversationCache() {
  const queryClient = useQueryClient();

  const patch = useCallback(
    (update: (list: ConversationResponse[]) => ConversationResponse[]) => {
      queryClient.setQueryData<ConversationPages>(conversationKeys.list, (data) =>
        data ? patchPages(data, update) : data
      );
    },
    [queryClient]
  );

  return useMemo(
    () => ({
      /** Add `conversation` at the top, or move it there. */
      upsert: (conversation: ConversationResponse) =>
        patch((list) => upsertConversation(list, conversation)),
      /** A message was sent to the conversation with `id`: move it to the top. */
      bump: (id: string) => patch((list) => moveToTop(list, id)),
      rename: (id: string, title: string) => patch((list) => renameConversation(list, id, title)),
      remove: (id: string) => patch((list) => removeConversation(list, id)),
    }),
    [patch]
  );
}
