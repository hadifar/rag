import type { HistoryMessageResponse } from '@/shared/types';
import type { ChatMessageInput } from '../types';
import { createBubbleHandler } from './chatStream';

/**
 * A saved conversation as the bubbles the live chat showed for it: each answer's events
 * are replayed through the same handler the stream uses.
 */
export function historyToMessages(history: HistoryMessageResponse[]): ChatMessageInput[] {
  const messages: ChatMessageInput[] = [];
  const append = (msg: ChatMessageInput) => String(messages.push(msg) - 1);
  const update = (id: string, msg: ChatMessageInput) => {
    messages[Number(id)] = msg;
  };

  for (const message of history) {
    if (message.role === 'user') {
      messages.push({ type: 'text', content: { text: message.text }, position: 'right' });
    } else {
      message.events.forEach(createBubbleHandler(append, update));
    }
  }
  return messages;
}
