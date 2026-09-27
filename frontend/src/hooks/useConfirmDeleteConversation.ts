import { useCallback } from 'react';

import { useConversations } from './useConversations';

/** Asks the user to confirm, then deletes the conversation; tells them if that failed. */
export function useConfirmDeleteConversation(): (id: string) => void {
  const { deleteConversation } = useConversations();

  return useCallback(
    (id: string) => {
      if (!window.confirm('Delete this chat? This cannot be undone.')) return;
      deleteConversation(id).catch(() =>
        window.alert("Couldn't delete the chat. Please try again.")
      );
    },
    [deleteConversation]
  );
}
