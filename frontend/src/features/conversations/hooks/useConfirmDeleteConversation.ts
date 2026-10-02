import { useCallback, useState } from 'react';

import type { ConversationResponse } from '@/shared/types';
import { useConversations } from './useConversations';

const DELETE_FAILED = "Couldn't delete the chat. Please try again.";

type ConfirmDeleteConversation = {
  /** Opens the confirmation for this conversation. */
  requestDelete: (conversation: ConversationResponse) => void;
  /** The conversation awaiting confirmation, or null when nothing is being asked. */
  pending: ConversationResponse | null;
  isDeleting: boolean;
  error: string | null;
  confirm: () => void;
  cancel: () => void;
};

/** Holds a delete until the user confirms it; a failure stays in the dialog so they can retry. */
export function useConfirmDeleteConversation(): ConfirmDeleteConversation {
  const { deleteConversation } = useConversations();
  const [pending, setPending] = useState<ConversationResponse | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const requestDelete = useCallback((conversation: ConversationResponse) => {
    setError(null);
    setPending(conversation);
  }, []);

  const cancel = useCallback(() => {
    // Closing mid-request would hide whether the delete worked.
    if (!isDeleting) setPending(null);
  }, [isDeleting]);

  const confirm = useCallback(() => {
    if (!pending || isDeleting) return;
    setIsDeleting(true);
    setError(null);
    deleteConversation(pending.id)
      .then(() => setPending(null))
      .catch(() => setError(DELETE_FAILED))
      .finally(() => setIsDeleting(false));
  }, [pending, isDeleting, deleteConversation]);

  return { requestDelete, pending, isDeleting, error, confirm, cancel };
}
