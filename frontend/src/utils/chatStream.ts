import type { ChatMessageInput, ChatStreamEvent } from '../types/chat';

type AppendMessage = (msg: ChatMessageInput) => string;
type UpdateMessage = (id: string, msg: ChatMessageInput) => void;

/** The streamed events that become bubbles; the rest update the sidebar or the URL. */
export type BubbleEvent = Extract<
  ChatStreamEvent,
  { type: 'text' | 'tool_start' | 'tool_result' | 'sources' }
>;

export function assistantText(text: string): ChatMessageInput {
  return { type: 'text', content: { text } };
}

/**
 * Turns one answer's stream into bubbles: text deltas grow a single assistant bubble,
 * a tool call's bubble is filled in when its result arrives, and sources get their own.
 * Create one per answer.
 */
export function createBubbleHandler(append: AppendMessage, update: UpdateMessage) {
  let assistantMsgId: string | null = null;
  let assistantMsgText = '';
  let toolMsgId: string | null = null;

  return (event: BubbleEvent) => {
    switch (event.type) {
      case 'text':
        assistantMsgText += event.text;
        if (assistantMsgId === null) {
          assistantMsgId = append(assistantText(assistantMsgText));
        } else {
          update(assistantMsgId, assistantText(assistantMsgText));
        }
        break;
      case 'tool_start':
        toolMsgId = append({
          type: 'tool',
          content: { name: event.name, query: event.query, status: 'pending' },
        });
        break;
      case 'tool_result':
        if (toolMsgId !== null) {
          update(toolMsgId, {
            type: 'tool',
            content: { name: event.name, output: event.output, status: 'done' },
          });
        }
        break;
      case 'sources':
        if (event.names.length > 0) {
          append({ type: 'sources', content: { names: event.names } });
        }
        break;
    }
  };
}
