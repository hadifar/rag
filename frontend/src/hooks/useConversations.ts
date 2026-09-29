import { createContext, use } from 'react';

import type { ConversationsContextValue } from '../types';

export const ConversationsContext = createContext<ConversationsContextValue | null>(null);

export function useConversations(): ConversationsContextValue {
  const context = use(ConversationsContext);
  if (context === null) {
    throw new Error('useConversations must be used within an ConversationsProvider');
  }
  return context;
}
