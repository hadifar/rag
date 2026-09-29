import { useCallback, useEffect, useRef, useState } from 'react';

import type { ChatMessage, ChatMessageInput } from '../types';

/** The chat's bubbles, each given a stable id so it can be updated or removed later. */
export function useMessageList() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const nextId = useRef(0);
  // update() lands once per streamed token; batching to one commit per animation frame
  // keeps a long answer from rebuilding the whole array (and re-parsing its markdown,
  // and re-running scrollIntoView) hundreds of times instead of a handful.
  const pendingUpdates = useRef(new Map<string, ChatMessageInput>());
  const flushHandle = useRef<number | null>(null);

  const withId = useCallback(
    (msg: ChatMessageInput, id = String(nextId.current++)) => ({ ...msg, id }) as ChatMessage,
    []
  );

  const flush = useCallback(() => {
    flushHandle.current = null;
    const pending = pendingUpdates.current;
    if (pending.size === 0) return;
    setMessages((prev) =>
      prev.map((m) => {
        const next = pending.get(m.id);
        return next === undefined ? m : withId(next, m.id);
      })
    );
    pending.clear();
  }, [withId]);

  useEffect(() => {
    return () => {
      if (flushHandle.current !== null) cancelAnimationFrame(flushHandle.current);
    };
  }, []);

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
      pendingUpdates.current.set(id, msg);
      flushHandle.current ??= requestAnimationFrame(flush);
    },
    [flush]
  );

  const remove = useCallback((id: string) => {
    setMessages((prev) => prev.filter((m) => m.id !== id));
  }, []);

  /** Shows the typing bubble; returns a function that hides it (calling it again is a no-op). */
  const showTyping = useCallback(() => {
    const id = append({ type: 'typing' });
    let shown = true;
    return () => {
      if (!shown) return;
      shown = false;
      remove(id);
    };
  }, [append, remove]);

  const replace = useCallback(
    (inputs: ChatMessageInput[]) => setMessages(inputs.map((msg) => withId(msg))),
    [withId]
  );

  return { messages, append, update, showTyping, replace };
}
