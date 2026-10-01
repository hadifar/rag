import type { ChatMessageInput, HistoryMessageResponse } from '../types';

/** A saved conversation as the bubbles the live chat would have shown for it. */
export function historyToMessages(history: HistoryMessageResponse[]): ChatMessageInput[] {
  return history.flatMap((message): ChatMessageInput[] => {
    if (message.role === 'user') {
      return [{ type: 'text', content: { text: message.text }, position: 'right' }];
    }
    const answer: ChatMessageInput = { type: 'text', content: { text: message.text } };
    // null: the answer didn't search; [] searched and found nothing (still shown).
    return message.references !== null
      ? [answer, { type: 'references', content: { references: message.references } }]
      : [answer];
  });
}
