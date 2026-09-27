import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

import type { ChatStreamEvent, Schemas } from '../src/types';

type SseEvent = { [T in ChatStreamEvent['type']]: [T, unknown] }[ChatStreamEvent['type']];

/** A finished `text/event-stream` response, framed the way the backend sends it. */
export function sse(events: SseEvent[]) {
  const body = events
    .map(([event, data]) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`)
    .join('');
  return new HttpResponse(body, { headers: { 'Content-Type': 'text/event-stream' } });
}

export const emptyConversationPage: Schemas['ConversationPageResponse'] = {
  items: [],
  next_cursor: null,
};

/** The fake backend every test starts from; a test overrides a route with `server.use`. */
export const server = setupServer(
  http.get('/api/conversations', () => HttpResponse.json(emptyConversationPage)),
);
