import { useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

import { ApiError } from '../api/client';
import { streamChat } from '../api/chat';
import { openKbSource } from '../api/kb';
import {
  createConversation,
  fetchConversationMessages,
  generateTitle,
  touchConversation,
} from '../api/conversations';
import { useConversations } from './useConversations';
import { assistantText, createBubbleHandler } from '../utils/chatStream';
import { conversationPath } from '../utils/conversations';
import { historyToMessages } from '../utils/history';
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
  const { messages, append, update, showTyping, replace } = useMessageList();

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

  // The conversation a message goes to: the one on screen, or a new one, which the URL
  // then follows before anything streams.
  const openConversation = useCallback(
    async (signal: AbortSignal): Promise<{ id: string; isNew: boolean }> => {
      const current = conversationIdRef.current;
      if (current) {
        await touchConversation(current, signal);
        bump(current);
        return { id: current, isNew: false };
      }
      const conversation = await createConversation(signal);
      upsert(conversation);
      conversationIdRef.current = conversation.id; // before navigating, so it isn't reloaded
      navigate(conversationPath(conversation.id), { replace: true });
      return { id: conversation.id, isNew: true };
    },
    [bump, upsert, navigate]
  );

  // Gives a new chat a proper title from its first message, without waiting for the answer.
  // If the request itself fails the conversation stays untitled until reloaded.
  const nameConversation = useCallback(
    async (id: string, message: string) => {
      const { title } = await generateTitle(id, message).catch(() => ({ title: null }));
      if (title) rename(id, title);
    },
    [rename]
  );

  const sendMessage = useCallback(
    async (val: string) => {
      const text = val.trim();
      if (!text) return;

      // A new turn supersedes whatever is still streaming.
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      append({ type: 'text', content: { text }, position: 'right' });
      const hideTyping = showTyping();
      const showBubble = createBubbleHandler(append, update);

      try {
        const { id, isNew } = await openConversation(controller.signal);
        if (isNew) void nameConversation(id, text);
        await streamChat({
          conversationId: id,
          message: text,
          onEvent: (event) => {
            hideTyping();
            showBubble(event);
          },
          signal: controller.signal,
        });
      } catch (err) {
        if (!controller.signal.aborted) {
          const message = err instanceof Error ? err.message : String(err);
          append(assistantText(`Something went wrong: ${message}`));
        }
      } finally {
        hideTyping();
        if (abortRef.current === controller) abortRef.current = null;
      }
    },
    [append, update, showTyping, openConversation, nameConversation]
  );

  /** Opens a cited knowledge-base document in a new tab. */
  const openSource = useCallback((name: string) => {
    openKbSource(name).catch(() => window.alert("Couldn't open that document. Please try again."));
  }, []);

  return { messages, sendMessage, openSource };
}
