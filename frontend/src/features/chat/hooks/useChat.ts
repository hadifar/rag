import { useCallback } from 'react';

import { isWaiting, retryable } from '../model/transcript';
import { useAttachmentDrafts } from './useAttachmentDrafts';
import { useRunSettings } from './useRunSettings';
import { useSendMessage } from './useSendMessage';
import { useTranscript } from './useTranscript';

/** The chat page's state: `conversationId` is the one in the URL; undefined for a new chat. */
export function useChat(conversationId: string | undefined) {
  const transcript = useTranscript(conversationId);
  const sendMessage = useSendMessage(conversationId);
  const attachments = useAttachmentDrafts(conversationId);
  const run = useRunSettings();
  const { settings } = run;
  const { take } = attachments;
  const failed = retryable(transcript);
  const question = failed?.question;
  // The bubble's own array: stable while the transcript doesn't change.
  const questionAttachments = failed?.attachments;

  // Sends the text with the files uploaded for it, to the conversation they're in.
  const send = useCallback(
    (text: string) => {
      const { attachments: files, conversation } = take();
      void sendMessage(text, files, conversation);
    },
    [sendMessage, take]
  );

  // Sends the failed question again as a new turn, as the saved history will show it,
  // with the same attachments: they're still in the conversation.
  const retry = useCallback(() => {
    if (question !== undefined) void sendMessage(question, questionAttachments);
  }, [question, questionAttachments, sendMessage]);

  return {
    conversationId,
    bubbles: transcript.bubbles,
    isWaiting: isWaiting(transcript),
    // Only a new chat: an existing one is also empty for a moment while its history loads.
    showWelcome: !conversationId && transcript.bubbles.length === 0,
    sendMessage: send,
    attachments: {
      drafts: attachments.drafts,
      notice: attachments.notice,
      uploading: attachments.uploading,
      hasReady: attachments.hasReady,
      onAttach: attachments.attach,
      onRemove: attachments.remove,
    },
    run: {
      model: settings.model,
      effort: settings.effort,
      onModel: run.setModel,
      onEffort: run.setEffort,
    },
    retryBubbleId: failed?.bubbleId ?? null,
    retry,
  };
}
