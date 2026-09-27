import type { Schemas } from '../types';
import type { ChatMessageInput } from '../types/chat';

/** A saved conversation as the bubbles the live chat would have shown for it. */
export function historyToMessages(history: Schemas['HistoryMessageResponse'][]): ChatMessageInput[] {
  return history.flatMap((message): ChatMessageInput[] => {
    if (message.role === 'user') {
      return [{ type: 'text', content: { text: message.text }, position: 'right' }];
    }
    const answer: ChatMessageInput = { type: 'text', content: { text: message.text } };
    return message.sources.length > 0
      ? [answer, { type: 'sources', content: { names: message.sources } }]
      : [answer];
  });
}
