import { useCallback, useMemo, useState, useTransition } from 'react';
import type { ReactNode } from 'react';
import { useMatch, useNavigate } from 'react-router-dom';

import { deleteConversation as apiDeleteConversation, listConversations } from '../api/conversations';
import {
  appendPage,
  moveToTop,
  removeConversation,
  renameConversation,
  upsertConversation,
} from '../utils/conversations';
import type { ConversationResponse, LoadStatus } from '../types';
import { ConversationsContext } from '../hooks/useConversations';
import { useLoadOnMount } from '../hooks/useLoadOnMount';

export function ConversationsProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const openConversation = useMatch('/chat/:conversationId')?.params.conversationId;

  const [conversations, setConversations] = useState<ConversationResponse[]>([]);
  const [status, setStatus] = useState<LoadStatus>('loading');
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [isLoadingMore, startLoadingMore] = useTransition();

  useLoadOnMount(
    (signal) => listConversations(null, signal),
    (page) => {
      setConversations(page.items);
      setNextCursor(page.next_cursor);
      setStatus('ready');
    },
    () => setStatus('error')
  );

  const loadMore = useCallback(() => {
    if (!nextCursor || isLoadingMore) return;
    startLoadingMore(async () => {
      // Caught here: an error escaping a transition goes to the route's error page.
      // On failure the button just re-enables, so the user can try again.
      try {
        const page = await listConversations(nextCursor);
        // Updates after an `await` need their own startTransition to stay in it.
        startLoadingMore(() => {
          setConversations((list) => appendPage(list, page.items));
          setNextCursor(page.next_cursor);
        });
      } catch {
        // Nothing to show: the list and cursor are unchanged.
      }
    });
  }, [nextCursor, isLoadingMore]);

  const upsert = useCallback((conversation: ConversationResponse) => {
    setConversations((list) => upsertConversation(list, conversation));
  }, []);

  const bump = useCallback((id: string) => {
    setConversations((list) => moveToTop(list, id));
  }, []);

  const rename = useCallback((id: string, title: string) => {
    setConversations((list) => renameConversation(list, id, title));
  }, []);

  const deleteConversation = useCallback(
    async (id: string) => {
      await apiDeleteConversation(id);
      setConversations((list) => removeConversation(list, id));
      if (openConversation === id) navigate('/chat', { replace: true });
    },
    [openConversation, navigate]
  );

  const value = useMemo(
    () => ({
      conversations,
      status,
      hasMore: nextCursor !== null,
      isLoadingMore,
      loadMore,
      upsert,
      bump,
      rename,
      deleteConversation,
    }),
    [
      conversations,
      status,
      nextCursor,
      isLoadingMore,
      loadMore,
      upsert,
      bump,
      rename,
      deleteConversation,
    ]
  );

  return <ConversationsContext value={value}>{children}</ConversationsContext>;
}
