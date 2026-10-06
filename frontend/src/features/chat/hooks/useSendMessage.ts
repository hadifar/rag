import { useCallback, useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';

import {
  createConversation,
  generateTitle,
  useConversationCache,
} from '@/features/conversations';
import { errorMessage } from '@/shared/api/errors';
import type { StreamEventResponse } from '@/shared/types';
import { routes } from '@/shared/routes';
import { streamChat } from '../api/chat';
import { chatKeys } from '../api/queryKeys';
import { applyEvents, emptyTranscript, endTurn, startTurn } from '../model/transcript';
import type { Transcript } from '../types';
import { frameBatcher } from './frameBatcher';

/** Why the answer stopped, for the user: never the raw error, which reads as gibberish. */
function answerErrorText(err: unknown): string {
  // fetch fails with a TypeError when the request never got a response.
  if (err instanceof TypeError) return "Couldn't reach the server. Check your connection and try again.";
  return errorMessage(
    err,
    { 404: 'This conversation no longer exists.' },
    'Something went wrong while answering. Please try again.'
  );
}

/** The answer being streamed: which conversation it's for, and how to stop it. */
type Stream = { conversationId: string | undefined; controller: AbortController };

/**
 * Sends the user's message and streams the answer into the conversation's transcript.
 * `conversationId` is the one on screen (undefined for a new chat, which is created on
 * its first message and then followed by the URL). Leaving the conversation stops it.
 */
export function useSendMessage(conversationId: string | undefined) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { upsert, bump, rename } = useConversationCache();
  const active = useRef<Stream | null>(null);

  // Navigating to another conversation (sidebar, New chat, back/forward) stops the
  // answer. The URL catching up with a new chat's id isn't leaving it.
  useEffect(() => {
    if (active.current && active.current.conversationId !== conversationId) {
      active.current.controller.abort();
      active.current = null;
    }
  }, [conversationId]);

  useEffect(() => () => active.current?.controller.abort(), []);

  // Gives a new chat a proper title from its first message, without waiting for the answer.
  // If the request itself fails the conversation stays untitled until reloaded.
  const nameConversation = useCallback(
    async (id: string, message: string) => {
      const { title } = await generateTitle(id, message).catch(() => ({ title: null }));
      if (title) rename(id, title);
    },
    [rename]
  );

  return useCallback(
    async (val: string) => {
      const text = val.trim();
      if (!text) return;

      // A new turn supersedes whatever is still streaming.
      active.current?.controller.abort();
      const controller = new AbortController();
      const stream: Stream = { conversationId, controller };
      active.current = stream;

      // Writes stop once the answer is aborted, so a stopped stream can't leave a
      // half-written answer in the cache after its conversation was left.
      const write = (update: (t: Transcript) => Transcript) => {
        if (controller.signal.aborted) return;
        queryClient.setQueryData<Transcript>(chatKeys.transcript(stream.conversationId), (t) =>
          update(t ?? emptyTranscript())
        );
      };
      const events = frameBatcher<StreamEventResponse>((batch) => write((t) => applyEvents(t, batch)));
      controller.signal.addEventListener('abort', events.cancel);

      // A history load still in flight would overwrite the new turn when it lands.
      await queryClient.cancelQueries({ queryKey: chatKeys.transcript(conversationId), exact: true });
      // A new chat starts from nothing, not from whatever an earlier new chat left there.
      write((t) => startTurn(conversationId ? t : emptyTranscript(), text));

      try {
        if (conversationId) {
          // The server lists it first too, as it takes the message.
          bump(conversationId);
        } else {
          const conversation = await createConversation(controller.signal);
          upsert(conversation);
          void nameConversation(conversation.id, text);
          // Move what's on screen to the new chat's own entry, then let the URL follow.
          const shown = queryClient.getQueryData<Transcript>(chatKeys.transcript(undefined));
          queryClient.setQueryData(chatKeys.transcript(conversation.id), shown);
          stream.conversationId = conversation.id;
          navigate(routes.chat(conversation.id), { replace: true });
        }
        await streamChat({
          conversationId: stream.conversationId!,
          message: text,
          onEvent: events.push,
          signal: controller.signal,
        });
        events.flushNow();
        write((t) => endTurn(t));
      } catch (err) {
        events.flushNow();
        write((t) => endTurn(t, answerErrorText(err)));
      } finally {
        if (active.current === stream) active.current = null;
      }
    },
    [conversationId, queryClient, navigate, upsert, bump, nameConversation]
  );
}
