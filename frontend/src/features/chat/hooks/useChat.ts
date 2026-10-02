import { isWaiting } from '../model/transcript';
import { useSendMessage } from './useSendMessage';
import { useTranscript } from './useTranscript';

/** The chat page's state: `conversationId` is the one in the URL; undefined for a new chat. */
export function useChat(conversationId: string | undefined) {
  const transcript = useTranscript(conversationId);
  const sendMessage = useSendMessage(conversationId);

  return {
    bubbles: transcript.bubbles,
    isWaiting: isWaiting(transcript),
    // Only a new chat: an existing one is also empty for a moment while its history loads.
    showWelcome: !conversationId && transcript.bubbles.length === 0,
    sendMessage,
  };
}
