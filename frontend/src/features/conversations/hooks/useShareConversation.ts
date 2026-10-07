import { useCallback, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { errorMessage, ignoreNotFound } from '@/shared/api/errors';
import { loadStatus } from '@/shared/api/queryClient';
import type { ConversationResponse, ShareResponse } from '@/shared/types';
import { fetchShare, shareConversation, unshareConversation } from '../api/conversations';
import { conversationKeys } from '../api/queryKeys';
import { sharedOn, shareUrl } from '../model/conversations';

const GONE = 'This chat no longer exists.';
const LOAD_FAILED = "Couldn't load this chat's link. Please try again.";
const SHARE_FAILED = "Couldn't share the chat. Please try again.";
const NOTHING_TO_SHARE = 'This chat has no messages to share yet.';
const STOP_FAILED = "Couldn't stop sharing the chat. Please try again.";
const COPY_FAILED = "Couldn't copy the link. Select it and copy it yourself.";

/**
 * The share dialog of one conversation at a time: its public link, if it has one, and
 * the actions on it. A link shows the chat as it was when shared (a snapshot); sharing
 * again updates it behind the same link.
 */
export function useShareConversation() {
  const queryClient = useQueryClient();
  const [sharing, setSharing] = useState<ConversationResponse | null>(null);
  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'failed'>('idle');
  const id = sharing?.id;

  const query = useQuery({
    queryKey: conversationKeys.share(id ?? ''),
    queryFn: ({ signal }) => fetchShare(id!, signal),
    enabled: id !== undefined,
  });

  const setShare = useCallback(
    (conversationId: string, share: ShareResponse | null) =>
      queryClient.setQueryData(conversationKeys.share(conversationId), share),
    [queryClient]
  );

  const save = useMutation({
    mutationFn: (conversationId: string) => shareConversation(conversationId),
    onSuccess: (share, conversationId) => {
      setShare(conversationId, share);
      setCopyState('idle');
    },
  });

  const stop = useMutation({
    // Already gone (the chat was deleted) is unshared too.
    mutationFn: (conversationId: string) => ignoreNotFound(unshareConversation(conversationId)),
    onSuccess: (_, conversationId) => setShare(conversationId, null),
  });

  const { mutate: mutateSave, reset: resetSave } = save;
  const { mutate: mutateStop, reset: resetStop } = stop;
  const share = query.data ?? null;
  const link = share ? shareUrl(window.location.origin, share.id) : null;

  const open = useCallback(
    (conversation: ConversationResponse) => {
      resetSave();
      resetStop();
      setCopyState('idle');
      setSharing(conversation);
    },
    [resetSave, resetStop]
  );

  const close = useCallback(() => setSharing(null), []);

  const saveShare = useCallback(() => {
    if (id) mutateSave(id);
  }, [id, mutateSave]);

  const stopSharing = useCallback(() => {
    if (id) mutateStop(id);
  }, [id, mutateStop]);

  const copy = useCallback(() => {
    if (!link) return;
    navigator.clipboard.writeText(link).then(
      () => setCopyState('copied'),
      () => setCopyState('failed')
    );
  }, [link]);

  const error = save.isError
    ? errorMessage(save.error, { 404: GONE, 409: NOTHING_TO_SHARE }, SHARE_FAILED)
    : stop.isError
      ? STOP_FAILED
      : query.isError
        ? errorMessage(query.error, { 404: GONE }, LOAD_FAILED)
        : copyState === 'failed'
          ? COPY_FAILED
          : null;

  return {
    /** The conversation whose dialog is open, or null. */
    sharing,
    open,
    close,
    status: loadStatus(query),
    /** The public link, or null while it isn't shared. */
    link,
    /** When its snapshot was taken, for display; null while it isn't shared. */
    sharedOn: share ? sharedOn(share.shared_at) : null,
    /** Shares it as it is now: a new link, or a new snapshot behind the current one. */
    saveShare,
    isSaving: save.isPending,
    stopSharing,
    isStopping: stop.isPending,
    copy,
    copied: copyState === 'copied',
    error,
  };
}
