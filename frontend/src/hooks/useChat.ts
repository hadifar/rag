import { useCallback, useEffect, useRef, useState } from 'react';
import { streamChat } from '../api/chat';
import type { ChatMessage, ChatStreamEvent, ChatMessageInput } from '../types/chat';

function assistantText(text: string): ChatMessageInput {
  return { type: 'text', content: { text } };
}


function createStreamHandler(
  appendMsg: (msg: ChatMessageInput) => string,
  updateMsg: (id: string, msg: ChatMessageInput) => void,
) {
  let assistantMsgId: string | null = null;
  let assistantMsgText = '';
  let toolMsgId: string | null = null;

  return (event: ChatStreamEvent) => {
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
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const nextId = useRef(0);
  const threadIdRef = useRef(crypto.randomUUID());
  const abortRef = useRef<AbortController | null>(null);

  const appendMsg = useCallback((msg: ChatMessageInput): string => {
    const id = String(nextId.current++);
    setMessages((prev) => [...prev, { ...msg, id } as ChatMessage]);
    return id;
  }, []);

  const updateMsg = useCallback((id: string, msg: ChatMessageInput) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? ({ ...msg, id } as ChatMessage) : m)));
  }, []);

  const deleteMsg = useCallback((id: string) => {
    setMessages((prev) => prev.filter((m) => m.id !== id));
  }, []);

  // Cancel any in-flight stream when the component unmounts.
  useEffect(() => () => abortRef.current?.abort(), []);

  const sendMessage = useCallback(
    async (val: string) => {
      const text = val.trim();
      if (!text) return;

      // A new turn supersedes whatever is still streaming.
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      appendMsg({ type: 'text', content: { text }, position: 'right' });

      const typingId = appendMsg({ type: 'typing' });
      let typingCleared = false;
      const clearTyping = () => {
        if (typingCleared) return;
        typingCleared = true;
        deleteMsg(typingId);
      };

      const handleStreamEvent = createStreamHandler(appendMsg, updateMsg);
      const onEvent = (event: ChatStreamEvent) => {
        clearTyping();
        handleStreamEvent(event);
      };

      try {
        await streamChat({ message: text, thread_id: threadIdRef.current, onEvent, signal: controller.signal });
      } catch (err) {
        if (!controller.signal.aborted) {
          const message = err instanceof Error ? err.message : String(err);
          appendMsg(assistantText(`Something went wrong: ${message}`));
        }
      } finally {
        clearTyping();
        if (abortRef.current === controller) abortRef.current = null;
      }
    },
    [appendMsg, updateMsg, deleteMsg],
  );

  return { messages, sendMessage };
}
