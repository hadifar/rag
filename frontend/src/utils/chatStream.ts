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
  // FIFO: the backend doesn't send a call id, so this assumes tool calls resolve in the
  // order they started. True for the common case (one call, or calls that don't race);
  // genuinely concurrent calls need a call id from the backend to track precisely.
  const pendingToolMsgIds: string[] = [];

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
          pendingToolMsgIds.push(append({ type, content }));
          // Further text after a tool call starts a new bubble, so reading order stays
          // text → tool → text instead of the later text merging into the earlier bubble.
          assistantMsgId = null;
          assistantMsgText = '';
        } else {
          const toolMsgId = pendingToolMsgIds.shift();
          if (toolMsgId !== undefined) {
            update(toolMsgId, { type, content });
          }
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
