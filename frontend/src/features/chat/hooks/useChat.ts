import { useCallback } from 'react';

import { isWaiting, retryable } from '../model/transcript';
import { useSendMessage } from './useSendMessage';
import { useTranscript } from './useTranscript';

/** The chat page's state: `conversationId` is the one in the URL; undefined for a new chat. */
export function useChat(conversationId: string | undefined) {
  const transcript = useTranscript(conversationId);
  const sendMessage = useSendMessage(conversationId);
  const failed = retryable(transcript);
  const question = failed?.question;

  // Sends the failed question again as a new turn, as the saved history will show it.
  const retry = useCallback(() => {
    if (question !== undefined) void sendMessage(question);
  }, [question, sendMessage]);

  return {
    bubbles: transcript.bubbles,
    isWaiting: isWaiting(transcript),
    // Only a new chat: an existing one is also empty for a moment while its history loads.
    showWelcome: !conversationId && transcript.bubbles.length === 0,
    sendMessage,
    retryBubbleId: failed?.bubbleId ?? null,
    retry,
  };
}
