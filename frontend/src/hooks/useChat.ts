import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { ApiError } from '../api/base';
import { streamChat } from '../api/chat';
import { fetchConversationMessages } from '../api/conversations';
import { useAuth } from '../context/AuthContext';
import { useConversations } from '../context/ConversationsContext';
import { conversationPath } from '../utils/conversations';
import { historyToMessages } from '../utils/history';
import type { ChatMessage, ChatStreamEvent, ChatMessageInput } from '../types/chat';

function assistantText(text: string): ChatMessageInput {
  return { type: 'text', content: { text } };
}

function historyErrorText(err: unknown): string {
  return err instanceof ApiError && err.status === 404
    ? "This conversation doesn't exist or was deleted."
    : "Couldn't load this conversation. Please try again.";
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

/** `conversationId` is the one in the URL; undefined for a new, not yet sent chat. */
export function useChat(conversationId: string | undefined) {
  const { accessToken } = useAuth();
  const { upsert, rename } = useConversations();
  const navigate = useNavigate();
  const { key: locationKey } = useLocation();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const nextId = useRef(0);
  const abortRef = useRef<AbortController | null>(null);
  // The conversation new messages go to. Ahead of the URL for a moment: set as soon
  // as the server assigns a new conversation's id, before the URL is updated to it.
  const conversationIdRef = useRef(conversationId);
  // Set right before this hook updates the URL itself, so the effect below can tell
  // that apart from the user navigating (sidebar, New chat, back/forward).
  const selfNavigationRef = useRef(false);

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

  const replaceMessages = useCallback((inputs: ChatMessageInput[]) => {
    setMessages(inputs.map((msg) => ({ ...msg, id: String(nextId.current++) }) as ChatMessage));
  }, []);

  // Every user navigation (including "New chat" to the same /chat URL, hence the
  // location key) switches conversations: stop the old stream and load the new one.
  useEffect(() => {
    if (selfNavigationRef.current) {
      selfNavigationRef.current = false;
      return;
    }
    abortRef.current?.abort();
    conversationIdRef.current = conversationId;
    replaceMessages([]);
    if (!conversationId || !accessToken) return;

    const controller = new AbortController();
    fetchConversationMessages(conversationId, accessToken, controller.signal)
      .then((history) => replaceMessages(historyToMessages(history)))
      .catch((err: unknown) => {
        if (!controller.signal.aborted) replaceMessages([assistantText(historyErrorText(err))]);
      });
    return () => controller.abort();
  }, [conversationId, locationKey, accessToken, replaceMessages]);

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
            handleStreamEvent(event);
        }
      };

      try {
        await streamChat({
          message: text,
          conversation_id: conversationIdRef.current ?? null,
          accessToken: accessToken ?? '',
          onEvent,
          signal: controller.signal,
        });
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
    [appendMsg, updateMsg, deleteMsg, accessToken, upsert, rename, navigate],
  );

  return { messages, sendMessage };
}
