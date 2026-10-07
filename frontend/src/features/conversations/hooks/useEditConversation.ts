import { useCallback, useState } from 'react';
import { useMutation } from '@tanstack/react-query';

import { errorMessage } from '@/shared/api/errors';
import type { ConversationResponse } from '@/shared/types';
import { updateConversation } from '../api/conversations';
import { useConversationCache } from './useConversationCache';

const GONE = 'This chat no longer exists.';
const PIN_FAILED = "Couldn't update the chat. Please try again.";
const RENAME_FAILED = "Couldn't rename the chat. Please try again.";

/** A title as the server stores it: one line, without spaces around it. */
function tidyTitle(draft: string): string {
  return draft.split(/\s+/).filter(Boolean).join(' ');
}

type EditConversation = {
  /** Pins it, or unpins it if it's pinned. */
  togglePin: (conversation: ConversationResponse) => void;
  pinError: string | null;
  /** The conversation whose title is being edited, or null. */
  renamingId: string | null;
  startRename: (conversation: ConversationResponse) => void;
  /** Saves `draft` as its title; a blank or unchanged draft just ends the edit. */
  saveRename: (conversation: ConversationResponse, draft: string) => void;
  /** Ends the edit without saving; ignored while a save is on its way. */
  cancelRename: () => void;
  isSavingRename: boolean;
  /** Why the save failed; the edit stays open so the user can retry. */
  renameError: string | null;
};

/** Pins and renames conversations; each change moves the row to where the server now lists it. */
export function useEditConversation(): EditConversation {
  const { place } = useConversationCache();
  const [renamingId, setRenamingId] = useState<string | null>(null);

  const pin = useMutation({
    mutationFn: (conversation: ConversationResponse) =>
      updateConversation(conversation.id, { pinned: !conversation.pinned_at }),
    onSuccess: place,
  });

  const rename = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) => updateConversation(id, { title }),
    onSuccess: (conversation) => {
      place(conversation);
      setRenamingId(null);
    },
  });

  const { mutate: mutatePin, reset: resetPin } = pin;
  const { mutate: mutateRename, reset: resetRename, isPending: isSavingRename } = rename;

  const togglePin = useCallback(
    (conversation: ConversationResponse) => {
      resetPin();
      mutatePin(conversation);
    },
    [mutatePin, resetPin]
  );

  const startRename = useCallback(
    (conversation: ConversationResponse) => {
      resetRename();
      setRenamingId(conversation.id);
    },
    [resetRename]
  );

  const cancelRename = useCallback(() => {
    if (!isSavingRename) setRenamingId(null);
  }, [isSavingRename]);

  const saveRename = useCallback(
    (conversation: ConversationResponse, draft: string) => {
      const title = tidyTitle(draft);
      if (!title || title === conversation.title) setRenamingId(null);
      else if (!isSavingRename) mutateRename({ id: conversation.id, title });
    },
    [isSavingRename, mutateRename]
  );

  return {
    togglePin,
    pinError: pin.isError ? errorMessage(pin.error, { 404: GONE }, PIN_FAILED) : null,
    renamingId,
    startRename,
    saveRename,
    cancelRename,
    isSavingRename,
    renameError: rename.isError ? errorMessage(rename.error, { 404: GONE }, RENAME_FAILED) : null,
  };
}
