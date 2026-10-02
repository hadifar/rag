import type { ChatMessageInput, StreamEventResponse } from '../types';

type AppendMessage = (msg: ChatMessageInput) => string;
type UpdateMessage = (id: string, msg: ChatMessageInput) => void;
type RemoveMessage = (id: string) => void;

export function assistantText(text: string): ChatMessageInput {
  return { type: 'text', content: { text } };
}

function reasoning(text: string, streaming: boolean): ChatMessageInput {
  return { type: 'reasoning', content: { text, streaming } };
}

/**
 * Turns one answer's stream into bubbles: text deltas grow a single assistant bubble,
 * reasoning deltas a single reasoning bubble (until the model answers or calls a tool),
 * a tool's bubble is filled in when it's `done`, the plan is one bubble rewritten in place
 * each time the agent updates it, and references get their own. A retracted answer's
 * bubble is removed; its revision starts a new one.
 * Create one per answer.
 */
export function createBubbleHandler(
  append: AppendMessage,
  update: UpdateMessage,
  remove: RemoveMessage
) {
  let assistantMsgId: string | null = null;
  let assistantMsgText = '';
  let reasoningMsgId: string | null = null;
  let reasoningMsgText = '';
  // FIFO: the backend doesn't send a call id, so this assumes tool calls resolve in the
  // order they started. True for the common case (one call, or calls that don't race);
  // genuinely concurrent calls need a call id from the backend to track precisely.
  const pendingToolMsgIds: string[] = [];
  let todosMsgId: string | null = null;

  return (event: StreamEventResponse) => {
    if (event.type === 'reasoning') {
      reasoningMsgText += event.text;
      if (reasoningMsgId === null) {
        reasoningMsgId = append(reasoning(reasoningMsgText, true));
      } else {
        update(reasoningMsgId, reasoning(reasoningMsgText, true));
      }
      return;
    }
    // Anything else ends the reasoning; more reasoning later (say, after a tool call)
    // starts a new bubble, as text does.
    if (reasoningMsgId !== null) {
      update(reasoningMsgId, reasoning(reasoningMsgText, false));
      reasoningMsgId = null;
      reasoningMsgText = '';
    }

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
      case 'todos': {
        const { type, ...content } = event;
        if (todosMsgId === null) {
          todosMsgId = append({ type, content });
          // Like a tool call: later text goes below the plan, not into a bubble above it.
          assistantMsgId = null;
          assistantMsgText = '';
        } else {
          update(todosMsgId, { type, content });
        }
        break;
      }
      case 'retracted':
        // The answer streamed since the last tool call or plan was rejected (not supported
        // by the searches): drop it before its revision streams.
        if (assistantMsgId !== null) {
          remove(assistantMsgId);
        }
        assistantMsgId = null;
        assistantMsgText = '';
        break;
      case 'references':
        // Sent only when the answer searched; an empty list still gets its bubble.
        append({ type: 'references', content: { references: event.references } });
        break;
      default:
        // A new backend event type fails to compile here until it's handled.
        event satisfies never;
    }
  };
}
