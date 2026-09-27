import { useCallback, useRef, useState } from 'react';

import type { ChatMessage, ChatMessageInput } from '../types';

/** The chat's bubbles, each given a stable id so it can be updated or removed later. */
export function useMessageList() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const nextId = useRef(0);

  const withId = useCallback(
    (msg: ChatMessageInput, id = String(nextId.current++)) => ({ ...msg, id }) as ChatMessage,
    []
  );

  /** Adds a bubble at the end and returns its id. */
  const append = useCallback(
    (msg: ChatMessageInput): string => {
      const message = withId(msg);
      setMessages((prev) => [...prev, message]);
      return message.id;
    },
    [withId]
  );

  const update = useCallback(
    (id: string, msg: ChatMessageInput) => {
      setMessages((prev) => prev.map((m) => (m.id === id ? withId(msg, id) : m)));
    },
    [withId]
  );

  const remove = useCallback((id: string) => {
    setMessages((prev) => prev.filter((m) => m.id !== id));
  }, []);

  const replace = useCallback(
    (inputs: ChatMessageInput[]) => setMessages(inputs.map((msg) => withId(msg))),
    [withId]
  );

  return { messages, append, update, remove, replace };
}
