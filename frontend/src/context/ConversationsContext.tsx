import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { useMatch, useNavigate } from 'react-router-dom';

import { deleteConversation as apiDeleteConversation, listConversations } from '../api/conversations';
import {
  appendPage,
  removeConversation,
  renameConversation,
  upsertConversation,
} from '../utils/conversations';
import type { Conversation } from '../utils/conversations';
import { useAuth } from './AuthContext';

type ListStatus = 'loading' | 'ready' | 'error';

type ConversationsContextValue = {
  conversations: Conversation[];
  status: ListStatus;
  hasMore: boolean;
  isLoadingMore: boolean;
  loadMore: () => Promise<void>;
  /** A turn started in `conversation`: add it, or move it to the top. */
  upsert: (conversation: Conversation) => void;
  rename: (id: string, title: string) => void;
  deleteConversation: (id: string) => Promise<void>;
};

const ConversationsContext = createContext<ConversationsContextValue | null>(null);

export function ConversationsProvider({ children }: { children: ReactNode }) {
  const { accessToken } = useAuth();
  const navigate = useNavigate();
  const openConversation = useMatch('/chat/:conversationId')?.params.conversationId;

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [status, setStatus] = useState<ListStatus>('loading');
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  useEffect(() => {
    if (!accessToken) return;
    let cancelled = false;
    listConversations(accessToken, null)
      .then((page) => {
        if (cancelled) return;
        setConversations(page.items);
        setNextCursor(page.next_cursor);
        setStatus('ready');
      })
      .catch(() => {
        if (!cancelled) setStatus('error');
      });
    return () => {
      cancelled = true;
    };
  }, [accessToken]);

  const loadMore = useCallback(async () => {
    if (!accessToken || !nextCursor || isLoadingMore) return;
    setIsLoadingMore(true);
    try {
      const page = await listConversations(accessToken, nextCursor);
      setConversations((list) => appendPage(list, page.items));
      setNextCursor(page.next_cursor);
    } finally {
      setIsLoadingMore(false);
    }
  }, [accessToken, nextCursor, isLoadingMore]);

  const upsert = useCallback((conversation: Conversation) => {
    setConversations((list) => upsertConversation(list, conversation));
  }, []);

  const rename = useCallback((id: string, title: string) => {
    setConversations((list) => renameConversation(list, id, title));
  }, []);

  const deleteConversation = useCallback(
    async (id: string) => {
      if (!accessToken) return;
      await apiDeleteConversation(id, accessToken);
      setConversations((list) => removeConversation(list, id));
      if (openConversation === id) navigate('/chat', { replace: true });
    },
    [accessToken, openConversation, navigate]
  );

  const value = useMemo(
    () => ({
      conversations,
      status,
      hasMore: nextCursor !== null,
      isLoadingMore,
      loadMore,
      upsert,
      rename,
      deleteConversation,
    }),
    [conversations, status, nextCursor, isLoadingMore, loadMore, upsert, rename, deleteConversation]
  );

  return <ConversationsContext.Provider value={value}>{children}</ConversationsContext.Provider>;
}

export function useConversations(): ConversationsContextValue {
  const context = useContext(ConversationsContext);
  if (context === null) {
    throw new Error('useConversations must be used within a ConversationsProvider');
  }
  return context;
}
