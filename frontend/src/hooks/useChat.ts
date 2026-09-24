import { useCallback, useRef } from 'react';
import { useMessages } from '@chatui/core';
import { streamChat } from '../api/chat';
import { USER, ASSISTANT } from '../components/avatars';
import type { ChatStreamEvent, TextContent, ToolContent, SourcesContent } from '../types/chat';

export function useChat() {
  const { messages, appendMsg, updateMsg, deleteMsg } = useMessages([]);
  const threadIdRef = useRef(crypto.randomUUID());
  const abortRef = useRef<AbortController | null>(null);


  const sendMessage = useCallback(
    async (type: string, val: string) => {
      if (type !== 'text' || !val.trim()) return;

      appendMsg({
        type: 'text',
        content: { text: val } satisfies TextContent,
        position: 'right',
        user: USER,
      });

      // Chat's built-in `isTyping` renders a typing Message without going
      // through renderMessageContent, so it shows nothing. Use a real message.
      let typingMsgId: string | null = appendMsg({ type: 'typing', user: ASSISTANT });
      const clearTyping = () => {
        if (typingMsgId !== null) deleteMsg(typingMsgId);
        typingMsgId = null;
      };

      let assistantMsgId: string | null = null;
      let assistantText = '';
      let toolMsgId: string | null = null;

      const controller = new AbortController();
      abortRef.current = controller;

      const onEvent = (event: ChatStreamEvent) => {
        clearTyping();
        switch (event.type) {
          case 'text':
            assistantText += event.text;
            if (assistantMsgId === null) {
              assistantMsgId = appendMsg({
                type: 'text',
                content: { text: assistantText } satisfies TextContent,
                user: ASSISTANT,
              });
            } else {
              updateMsg(assistantMsgId, {
                type: 'text',
                content: { text: assistantText } satisfies TextContent,
                user: ASSISTANT,
              });
            }
            break;
          case 'tool_start':
            toolMsgId = appendMsg({
              type: 'tool',
              content: {
                name: event.name,
                args: event.args,
                status: 'pending',
              } satisfies ToolContent,
              user: ASSISTANT,
            });
            break;
          case 'tool_result':
            if (toolMsgId !== null) {
              updateMsg(toolMsgId, {
                type: 'tool',
                content: {
                  name: event.name,
                  output: event.output,
                  status: 'done',
                } satisfies ToolContent,
                user: ASSISTANT,
              });
            }
            break;
          case 'sources':
            if (event.names.length > 0) {
              appendMsg({
                type: 'sources',
                content: { names: event.names } satisfies SourcesContent,
                user: ASSISTANT,
              });
            }
            break;
        }
      };

      try {
        await streamChat(val, threadIdRef.current, onEvent, controller.signal);
      } catch (err) {
        if (!controller.signal.aborted) {
          appendMsg({
            type: 'text',
            content: {
              text: `Something went wrong: ${(err as Error).message}`,
            } satisfies TextContent,
            user: ASSISTANT,
          });
        }
      } finally {
        clearTyping();
      }
    },
    [appendMsg, updateMsg, deleteMsg],
  );

  return { messages, sendMessage };
}
