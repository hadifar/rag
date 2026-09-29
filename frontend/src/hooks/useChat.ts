import { useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

import { ApiError } from '../api/client';
import { streamChat } from '../api/chat';
import { createConversation, fetchConversationMessages } from '../api/conversations';
import { useConversations } from './useConversations';
import { assistantText, createBubbleHandler } from '../utils/chatStream';
import { conversationPath } from '../utils/conversations';
import { historyToMessages } from '../utils/history';
import type { ChatStreamEvent } from '../types';
import { useMessageList } from './useMessageList';

function historyErrorText(err: unknown): string {
  return err instanceof ApiError && err.status === 404
    ? "This conversation doesn't exist or was deleted."
    : "Couldn't load this conversation. Please try again.";
}

/** `conversationId` is the one in the URL; undefined for a new, not yet sent chat. */
export function useChat(conversationId: string | undefined) {
  const { upsert, bump, rename } = useConversations();
  const navigate = useNavigate();
  const { messages, append, update, remove, replace } = useMessageList();

  const abortRef = useRef<AbortController | null>(null);
  // The conversation on screen, which new messages go to. Ahead of the URL for a
  // moment: a new chat's id is set here right before the URL is updated to it.
  const conversationIdRef = useRef<string | undefined>(undefined);

  // Navigating to another conversation (sidebar, New chat, back/forward) stops the
  // old stream and loads the new one. Skipped when the URL just caught up with the
  // conversation already on screen, i.e. a new chat's first message.
  useEffect(() => {
    if (conversationId && conversationId === conversationIdRef.current) return;
    abortRef.current?.abort();
    conversationIdRef.current = conversationId;
    replace([]);
    if (!conversationId) return;

    const controller = new AbortController();
    fetchConversationMessages(conversationId, controller.signal)
      .then((history) => replace(historyToMessages(history)))
      .catch((err: unknown) => {
        if (!controller.signal.aborted) replace([assistantText(historyErrorText(err))]);
      });
    return () => {
      controller.abort();
      // Not loaded after all, so the next run must load it (e.g. StrictMode's re-run).
      conversationIdRef.current = undefined;
    };
  }, [conversationId, replace]);

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

      append({ type: 'text', content: { text }, position: 'right' });

      const typingId = append({ type: 'typing' });
      let typingCleared = false;
      const clearTyping = () => {
        if (typingCleared) return;
        typingCleared = true;
        remove(typingId);
      };

      const showBubble = createBubbleHandler(append, update);
      const onEvent = (event: ChatStreamEvent) => {
        if (event.type === 'title') {
          rename(event.id, event.title);
          return;
        }
        clearTyping();
        showBubble(event);
      };

      try {
        let id = conversationIdRef.current;
        if (id) {
          bump(id);
        } else {
          // A new chat is created first; the URL follows it before anything streams.
          const conversation = await createConversation(controller.signal);
          upsert(conversation);
          id = conversation.id;
          conversationIdRef.current = id; // before navigating, so the chat isn't reloaded
          navigate(conversationPath(id), { replace: true });
        }
        await streamChat({
          conversationId: id,
          message: text,
          onEvent,
          signal: controller.signal,
        });
      } catch (err) {
        if (!controller.signal.aborted) {
          const message = err instanceof Error ? err.message : String(err);
          append(assistantText(`Something went wrong: ${message}`));
        }
      } finally {
        clearTyping();
        if (abortRef.current === controller) abortRef.current = null;
      }
    },
    [append, update, remove, upsert, bump, rename, navigate],
  );

  return { messages, sendMessage };
}
