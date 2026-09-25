import {
  EventStreamContentType,
  fetchEventSource,
} from '@microsoft/fetch-event-source';

import { apiUrl, jsonPost } from './base';
import type { ChatRequest } from '../types';
import type { ChatStreamEvent } from '../types/chat';

export interface StreamChatArgs extends ChatRequest {
  onEvent: (event: ChatStreamEvent) => void;
  signal?: AbortSignal;
}

export function streamChat({ onEvent, signal, ...request }: StreamChatArgs): Promise<void> {

  return fetchEventSource(apiUrl('chat/stream'), {

    ...jsonPost(request),
    signal,
    openWhenHidden: true, // Keep the stream alive in a backgrounded tab

    async onopen(response) {
      const contentType = response.headers.get('content-type') ?? '';
      if (response.ok && contentType.startsWith(EventStreamContentType)) {
        return;
      }
      throw new Error(`chat stream failed to open: ${response.status}`);
    },

    onmessage(ev) {
      switch (ev.event) {
        case 'text':
          onEvent({ type: 'text', text: ev.data });
          break;
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
