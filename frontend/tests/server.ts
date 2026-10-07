import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

import type { ConversationPageResponse, StreamEventResponse } from '@/shared/types';

/** A finished `text/event-stream` response, framed the way the backend sends it. */
export function sse(events: StreamEventResponse[]) {
  const body = events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join('');
  return new HttpResponse(body, { headers: { 'Content-Type': 'text/event-stream' } });
}

export const emptyConversationPage: ConversationPageResponse = {
  items: [],
  next_cursor: null,
};

/** The fake backend every test starts from; a test overrides a route with `server.use`. */
export const server = setupServer(
  http.get('/api/conversations', () => HttpResponse.json(emptyConversationPage)),
  http.get('/api/conversations/pinned', () => HttpResponse.json([])),
  http.get('/api/skills', () => HttpResponse.json([])),
);
