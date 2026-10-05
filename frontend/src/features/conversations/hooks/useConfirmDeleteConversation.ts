import { useCallback, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useMatch, useNavigate } from 'react-router-dom';

import { ignoreNotFound } from '@/shared/api/errors';
import type { ConversationResponse } from '@/shared/types';
import { routePatterns, routes } from '@/shared/routes';
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
  /** Deleted conversations still on screen while their row plays its exit. */
  vanishing: ReadonlySet<string>;
  /** The row of `id` finished its exit: take it off the list. */
  finishVanish: (id: string) => void;
};

/** Holds a delete until the user confirms it; a failure stays in the dialog so they can retry. */
export function useConfirmDeleteConversation(): ConfirmDeleteConversation {
  const { remove } = useConversationCache();
  const navigate = useNavigate();
  const openConversation = useMatch(routePatterns.chat)?.params.conversationId;
  const [pending, setPending] = useState<ConversationResponse | null>(null);
  const [vanishing, setVanishing] = useState<ReadonlySet<string>>(new Set());

  const { mutate, reset, isPending, isError } = useMutation({
    // Already gone is success too; without this, a retry would 404 forever.
    mutationFn: (id: string) => ignoreNotFound(deleteConversation(id)),
    onSuccess: (_, id) => {
      // Stays listed until its row has played its exit; see finishVanish.
      setVanishing((ids) => new Set(ids).add(id));
      setPending(null);
      // Its page would show a chat that no longer exists.
      if (openConversation === id) navigate(routes.newChat, { replace: true });
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

  const finishVanish = useCallback(
    (id: string) => {
      remove(id);
      setVanishing((ids) => {
        const rest = new Set(ids);
        rest.delete(id);
        return rest;
      });
    },
    [remove]
  );

  return {
    requestDelete,
    pending,
    isDeleting: isPending,
    error: isError ? DELETE_FAILED : null,
    confirm,
    cancel,
    vanishing,
    finishVanish,
  };
}
