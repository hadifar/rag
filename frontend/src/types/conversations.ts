import type { ConversationResponse } from './api';
import type { LoadStatus } from './status';

export type ConversationsContextValue = {
  conversations: ConversationResponse[];
  status: LoadStatus;
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
