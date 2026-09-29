import { createContext, use } from 'react';

import type { ConversationResponse } from '../types';

export type ListStatus = 'loading' | 'ready' | 'error';

export type ConversationsContextValue = {
  conversations: ConversationResponse[];
  status: ListStatus;
  hasMore: boolean;
  isLoadingMore: boolean;
  loadMore: () => void;
  /** Add `conversation` at the top, or move it there. */
  upsert: (conversation: ConversationResponse) => void;
  /** A message was sent to the conversation with `id`: move it to the top. */
  bump: (id: string) => void;
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
