import { useCallback, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { ApiError } from '../api/client';
import { streamChat } from '../api/chat';
import { fetchConversationMessages } from '../api/conversations';
import { useConversations } from '../context/ConversationsContext';
import { assistantText, createBubbleHandler } from '../utils/chatStream';
import { conversationPath } from '../utils/conversations';
import { historyToMessages } from '../utils/history';
import type { ChatStreamEvent } from '../types/chat';
import { useMessageList } from './useMessageList';

function historyErrorText(err: unknown): string {
  return err instanceof ApiError && err.status === 404
    ? "This conversation doesn't exist or was deleted."
    : "Couldn't load this conversation. Please try again.";
}

/** `conversationId` is the one in the URL; undefined for a new, not yet sent chat. */
export function useChat(conversationId: string | undefined) {
  const { upsert, rename } = useConversations();
  const navigate = useNavigate();
  const { key: locationKey } = useLocation();
  const { messages, append, update, remove, replace } = useMessageList();

  const abortRef = useRef<AbortController | null>(null);
  // The conversation new messages go to. Ahead of the URL for a moment: set as soon
  // as the server assigns a new conversation's id, before the URL is updated to it.
  const conversationIdRef = useRef(conversationId);
  // Set right before this hook updates the URL itself, so the effect below can tell
  // that apart from the user navigating (sidebar, New chat, back/forward).
  const selfNavigationRef = useRef(false);

  // Every user navigation (including "New chat" to the same /chat URL, hence the
  // location key) switches conversations: stop the old stream and load the new one.
  useEffect(() => {
    if (selfNavigationRef.current) {
      selfNavigationRef.current = false;
      return;
    }
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
    return () => controller.abort();
  }, [conversationId, locationKey, replace]);

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
        switch (event.type) {
          case 'conversation': {
            const { id } = event.conversation;
            upsert(event.conversation);
            if (conversationIdRef.current !== id) {
              // A new conversation: follow its server-assigned id in the URL, without
              // reloading, since this stream is still delivering its first answer.
              conversationIdRef.current = id;
              selfNavigationRef.current = true;
              navigate(conversationPath(id), { replace: true });
            }
            return;
          }
          case 'title':
            rename(event.id, event.title);
            return;
          default:
            clearTyping();
            showBubble(event);
        }
      };

      try {
        await streamChat({
          message: text,
          conversation_id: conversationIdRef.current ?? null,
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
    [append, update, remove, upsert, rename, navigate],
  );

  return { messages, sendMessage };
}
