import {
  EventStreamContentType,
  fetchEventSource,
} from '@microsoft/fetch-event-source';

import type { ChatStreamEvent } from '../types/chat';

export function streamChat(
  message: string,
  threadId: string,
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {

  return fetchEventSource('api/chat/stream', {

    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, thread_id: threadId }),
    signal,
    openWhenHidden: true,

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
          const { name, args } = JSON.parse(ev.data);
          onEvent({ type: 'tool_start', name, args });
          break;
        }
        case 'tool_result': {
          const { name, output } = JSON.parse(ev.data);
          onEvent({ type: 'tool_result', name, output });
          break;
        }
      }
    },
    onerror(err) {
      // Rethrowing stops fetch-event-source's built-in infinite retry: a chat
      // turn should surface an error, not silently reconnect and resend.
      throw err;
    },
  });
}
