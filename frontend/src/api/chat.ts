import {
  EventStreamContentType,
  fetchEventSource,
} from '@microsoft/fetch-event-source';

import { ApiError, apiUrl, authFetch, jsonPostInit } from './client';
import type { ChatStreamEvent, Schemas } from '../types';

const STREAM_EVENT_TYPES: ReadonlySet<string> = new Set<ChatStreamEvent['type']>([
  'conversation',
  'title',
  'text',
  'tool_start',
  'tool_result',
  'sources',
]);

export type StreamChatArgs = Schemas['ChatRequest'] & {
  onEvent: (event: ChatStreamEvent) => void;
  signal?: AbortSignal;
};

export function streamChat({ onEvent, signal, ...request }: StreamChatArgs): Promise<void> {
  return fetchEventSource(apiUrl('chat/stream'), {
    ...jsonPostInit(request),
    // A 401 arrives before any event, so refresh-and-retry can't replay a partial stream.
    fetch: authFetch,
    signal,
    openWhenHidden: true, // Keep the stream alive in a backgrounded tab

    async onopen(response) {
      const contentType = response.headers.get('content-type') ?? '';
      if (response.ok && contentType.startsWith(EventStreamContentType)) {
        return;
      }
      throw new ApiError(response.status, `chat stream failed to open: ${response.status}`);
    },

    onmessage({ event, data }) {
      if (!STREAM_EVENT_TYPES.has(event)) return; // e.g. an event this client predates
      const payload = JSON.parse(data);
      // Each event's JSON is its fields, except `conversation`, which is the object itself.
      onEvent(
        (event === 'conversation'
          ? { type: event, conversation: payload }
          : { type: event, ...payload }) as ChatStreamEvent
      );
    },
    onerror(err) {
      throw err;
    },
  });
}
