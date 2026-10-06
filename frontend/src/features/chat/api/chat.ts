import {
  EventStreamContentType,
  fetchEventSource,
} from '@microsoft/fetch-event-source';

import { ApiError, apiUrl, authFetch, jsonPostInit } from '@/shared/api/client';
import type { MessageRequest, StreamEventResponse } from '@/shared/types';

export type StreamChatArgs = MessageRequest & {
  conversationId: string;
  onEvent: (event: StreamEventResponse) => void;
  signal?: AbortSignal;
};

/** Sends a message to a conversation and streams its answer as events. */
export function streamChat({
  conversationId,
  onEvent,
  signal,
  ...request
}: StreamChatArgs): Promise<void> {
  const path = `chat/${encodeURIComponent(conversationId)}`;
  return fetchEventSource(apiUrl(path), {
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

    onmessage({ data }) {
      // The server's keep-alive `: ping` comes through as an empty message; the SSE spec
      // says to drop it, but this library hands it over.
      if (!data) return;
      // Each event is one JSON object, told apart by its `type` (see StreamEventResponse).
      onEvent(JSON.parse(data) as StreamEventResponse);
    },
    onerror(err) {
      throw err;
    },
  });
}
