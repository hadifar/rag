import { useCallback, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useMatch, useNavigate } from 'react-router-dom';

import { ApiError } from '@/shared/api/client';
import type { ConversationResponse } from '@/shared/types';
import { deleteConversation } from '../api/conversations';
import { useConversationCache } from './useConversationCache';

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

async function deleteIfPresent(id: string): Promise<void> {
  try {
    await deleteConversation(id);
  } catch (err) {
    // A 404 means it's already gone — delete is idempotent, so that's success too,
    // not a failure to surface (and without this, a retry would 404 forever).
    if (!(err instanceof ApiError && err.status === 404)) throw err;
  }
}

/** Holds a delete until the user confirms it; a failure stays in the dialog so they can retry. */
export function useConfirmDeleteConversation(): ConfirmDeleteConversation {
  const { remove } = useConversationCache();
  const navigate = useNavigate();
  const openConversation = useMatch('/chat/:conversationId')?.params.conversationId;
  const [pending, setPending] = useState<ConversationResponse | null>(null);

  const { mutate, reset, isPending, isError } = useMutation({
    mutationFn: deleteIfPresent,
    onSuccess: (_, id) => {
      remove(id);
      setPending(null);
      // Its page would show a chat that no longer exists.
      if (openConversation === id) navigate('/chat', { replace: true });
    },
  });

  const requestDelete = useCallback(
    (conversation: ConversationResponse) => {
      reset();
      setPending(conversation);
    },
    [reset]
  );

  const cancel = useCallback(() => {
    // Closing mid-request would hide whether the delete worked.
    if (!isPending) setPending(null);
  }, [isPending]);

  const confirm = useCallback(() => {
    if (pending && !isPending) mutate(pending.id);
  }, [pending, isPending, mutate]);

  return {
    requestDelete,
    pending,
    isDeleting: isPending,
    error: isError ? DELETE_FAILED : null,
    confirm,
    cancel,
  };
}
