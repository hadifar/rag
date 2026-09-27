import {
  EventStreamContentType,
  fetchEventSource,
} from '@microsoft/fetch-event-source';

import { ApiError, apiUrl, authFetch, jsonPostInit } from './client';
import type { Schemas } from '../types';
import type { ChatStreamEvent } from '../types/chat';

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

    onmessage(ev) {
      switch (ev.event) {
        case 'conversation': {
          const conversation = JSON.parse(ev.data) as Schemas['ConversationResponse'];
          onEvent({ type: 'conversation', conversation });
          break;
        }
        case 'title': {
          const { id, title } = JSON.parse(ev.data) as { id: string; title: string };
          onEvent({ type: 'title', id, title });
          break;
        }
        case 'text': {
          const { text } = JSON.parse(ev.data) as { text: string };
          onEvent({ type: 'text', text });
          break;
        }
        case 'tool_start': {
          const { name, query } = JSON.parse(ev.data) as { name: string; query: string };
          onEvent({ type: 'tool_start', name, query });
          break;
        }
        case 'tool_result': {
          const { name, output } = JSON.parse(ev.data) as { name: string; output: string };
          onEvent({ type: 'tool_result', name, output });
          break;
        }
        case 'sources': {
          const { names } = JSON.parse(ev.data) as { names: string[] };
          onEvent({ type: 'sources', names });
          break;
        }
      }
    },
    onerror(err) {
      throw err;
    },
  });
}
