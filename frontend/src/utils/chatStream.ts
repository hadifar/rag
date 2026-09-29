import type { ChatMessageInput, StreamEventResponse } from '../types';

type AppendMessage = (msg: ChatMessageInput) => string;
type UpdateMessage = (id: string, msg: ChatMessageInput) => void;

export function assistantText(text: string): ChatMessageInput {
  return { type: 'text', content: { text } };
}

/**
 * Turns one answer's stream into bubbles: text deltas grow a single assistant bubble,
 * a tool's bubble is filled in when it's `done`, and sources get their own.
 * Create one per answer.
 */
export function createBubbleHandler(append: AppendMessage, update: UpdateMessage) {
  let assistantMsgId: string | null = null;
  let assistantMsgText = '';
  let toolMsgId: string | null = null;

  return (event: StreamEventResponse) => {
    switch (event.type) {
      case 'text':
        assistantMsgText += event.text;
        if (assistantMsgId === null) {
          assistantMsgId = append(assistantText(assistantMsgText));
        } else {
          update(assistantMsgId, assistantText(assistantMsgText));
        }
        break;
      case 'tool': {
        const { type, ...content } = event;
        if (content.status === 'pending') {
          toolMsgId = append({ type, content });
        } else if (toolMsgId !== null) {
          update(toolMsgId, { type, content });
        }
        break;
      }
      case 'sources':
        // Sent only when the answer searched; an empty list still gets its bubble.
        append({ type: 'sources', content: { sources: event.sources } });
        break;
      default:
        // A new backend event type fails to compile here until it's handled.
        event satisfies never;
    }
  };
}
