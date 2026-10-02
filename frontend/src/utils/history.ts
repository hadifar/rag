import type { ChatMessageInput, HistoryMessageResponse } from '../types';
import { createBubbleHandler } from './chatStream';

/**
 * A saved conversation as the bubbles the live chat showed for it: each answer's events
 * are replayed through the same handler the stream uses.
 */
export function historyToMessages(history: HistoryMessageResponse[]): ChatMessageInput[] {
  // Indexed by id; a removed bubble leaves a hole, so the ids of later ones hold.
  const messages: (ChatMessageInput | null)[] = [];
  const append = (msg: ChatMessageInput) => String(messages.push(msg) - 1);
  const update = (id: string, msg: ChatMessageInput) => {
    messages[Number(id)] = msg;
  };
  const remove = (id: string) => {
    messages[Number(id)] = null;
  };

  for (const message of history) {
    if (message.role === 'user') {
      messages.push({ type: 'text', content: { text: message.text }, position: 'right' });
    } else {
      message.events.forEach(createBubbleHandler(append, update, remove));
    }
  }
  return messages.filter((msg) => msg !== null);
}
