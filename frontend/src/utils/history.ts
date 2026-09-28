import type { ChatMessageInput, Schemas } from '../types';

/** A saved conversation as the bubbles the live chat would have shown for it. */
export function historyToMessages(history: Schemas['HistoryMessageResponse'][]): ChatMessageInput[] {
  return history.flatMap((message): ChatMessageInput[] => {
    if (message.role === 'user') {
      return [{ type: 'text', content: { text: message.text }, position: 'right' }];
    }
    const answer: ChatMessageInput = { type: 'text', content: { text: message.text } };
    // null: the answer didn't search; [] searched and found nothing (still shown).
    return message.sources !== null
      ? [answer, { type: 'sources', content: { sources: message.sources } }]
      : [answer];
  });
}
