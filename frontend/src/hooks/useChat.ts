import { useCallback, useRef, useState } from 'react';
import { useMessages } from '@chatui/core';
import { streamChat } from '../api/chat';
import { USER, ASSISTANT } from '../components/avatars';
import type { ChatStreamEvent, TextContent, ToolContent, SourcesContent } from '../types/chat';

const SOURCE_RE = /\[source: ([^\]]+)\]/g;

export function useChat() {
  const { messages, appendMsg, updateMsg } = useMessages([]);
  const [isTyping, setIsTyping] = useState(false);
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
      setIsTyping(true);

      let assistantMsgId: string | null = null;
      let assistantText = '';
      let toolMsgId: string | null = null;
      const sources = new Set<string>();

      const controller = new AbortController();
      abortRef.current = controller;

      const onEvent = (event: ChatStreamEvent) => {
        setIsTyping(false);
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
            for (const match of event.output.matchAll(SOURCE_RE)) {
              sources.add(match[1]);
            }
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
        setIsTyping(false);
        if (sources.size > 0) {
          appendMsg({
            type: 'sources',
            content: { names: [...sources].sort() } satisfies SourcesContent,
            user: ASSISTANT,
          });
        }
      }
    },
    [appendMsg, updateMsg],
  );

  return { messages, isTyping, sendMessage };
}
