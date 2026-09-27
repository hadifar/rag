import { createContext, use } from 'react';

import type { Conversation } from '../types';

export type ListStatus = 'loading' | 'ready' | 'error';

export type ConversationsContextValue = {
  conversations: Conversation[];
  status: ListStatus;
  hasMore: boolean;
  isLoadingMore: boolean;
  loadMore: () => void;
  /** A turn started in `conversation`: add it, or move it to the top. */
  upsert: (conversation: Conversation) => void;
  rename: (id: string, title: string) => void;
  deleteConversation: (id: string) => Promise<void>;
};

export const ConversationsContext = createContext<ConversationsContextValue | null>(null);

export function useConversations(): ConversationsContextValue {
  const context = use(ConversationsContext);
  if (context === null) {
    throw new Error('useConversations must be used within an ConversationsProvider');
  }
  return context;
}
