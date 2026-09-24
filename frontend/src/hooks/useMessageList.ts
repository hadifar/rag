import { useCallback, useRef, useState } from 'react';
import type { ChatMessage, ChatMessageInput } from '../types/chat';

export function useMessageList() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const nextId = useRef(0);

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

  return { messages, appendMsg, updateMsg, deleteMsg };
}
