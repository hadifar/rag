import { useCallback, useRef } from 'react';
import { useMessageList } from './useMessageList';
import { streamChat } from '../api/chat';
import type { ChatStreamEvent, ChatMessageInput } from '../types/chat';

function assistantText(text: string): ChatMessageInput {
  return { type: 'text', content: { text } };
}

// Show a typing message immediately and return a function that clears it
// (idempotent — safe to call more than once).
function showTyping(
  appendMsg: (msg: ChatMessageInput) => string,
  deleteMsg: (id: string) => void,
) {
  let id: string | null = appendMsg({ type: 'typing' });
  return () => {
    if (id !== null) deleteMsg(id);
    id = null;
  };
}

export function useChat() {
  const { messages, appendMsg, updateMsg, deleteMsg } = useMessageList();
  const threadIdRef = useRef(crypto.randomUUID());

  const sendMessage = useCallback(
    async (val: string) => {
      const text = val.trim();
      if (!text) return;

      appendMsg({ type: 'text', content: { text }, position: 'right' });

      const clearTyping = showTyping(appendMsg, deleteMsg);

      let assistantMsgId: string | null = null;
      let assistantMsgText = '';
      let toolMsgId: string | null = null;

      const controller = new AbortController();

      const onEvent = (event: ChatStreamEvent) => {
        clearTyping();
        switch (event.type) {
          case 'text':
            assistantMsgText += event.text;
            if (assistantMsgId === null) {
              assistantMsgId = appendMsg(assistantText(assistantMsgText));
            } else {
              updateMsg(assistantMsgId, assistantText(assistantMsgText));
            }
            break;
          case 'tool_start':
            toolMsgId = appendMsg({
              type: 'tool',
              content: { name: event.name, query: event.query, status: 'pending' },
            });
            break;
          case 'tool_result':
            if (toolMsgId !== null) {
              updateMsg(toolMsgId, {
                type: 'tool',
                content: { name: event.name, output: event.output, status: 'done' },
              });
            }
            break;
          case 'sources':
            if (event.names.length > 0) {
              appendMsg({ type: 'sources', content: { names: event.names } });
            }
            break;
        }
      };

      try {
        await streamChat(text, threadIdRef.current, onEvent, controller.signal);
      } catch (err) {
        if (!controller.signal.aborted) {
          const message = err instanceof Error ? err.message : String(err);
          appendMsg(assistantText(`Something went wrong: ${message}`));
        }
      } finally {
        clearTyping();
      }
    },
    [appendMsg, updateMsg, deleteMsg],
  );

  return { messages, sendMessage };
}
