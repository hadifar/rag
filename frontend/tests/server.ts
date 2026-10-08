import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

import type {
  ConversationPageResponse,
  RunSettingsResponse,
  SettingsResponse,
  StreamEventResponse,
  UploadLimitsResponse,
} from '@/shared/types';

/** A finished `text/event-stream` response, framed the way the backend sends it. */
export function sse(events: StreamEventResponse[]) {
  const body = events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join('');
  return new HttpResponse(body, { headers: { 'Content-Type': 'text/event-stream' } });
}

/** The backend's default UPLOADS__* limits (rag/config/uploads.py). */
export const uploadLimits: UploadLimitsResponse = {
  kb_max_bytes: 20 * 1024 * 1024,
  skill_max_bytes: 50 * 1024,
  skill_archive_max_bytes: 512 * 1024,
  attachment_max_bytes: 5 * 1024 * 1024,
};

export const emptyConversationPage: ConversationPageResponse = {
  items: [],
  next_cursor: null,
};

/** The fake backend every test starts from; a test overrides a route with `server.use`. */
export const server = setupServer(
  http.get('/api/conversations', () => HttpResponse.json(emptyConversationPage)),
  http.get('/api/conversations/pinned', () => HttpResponse.json([])),
  // The user's model and effort, at their defaults.
  http.get('/api/settings/me', () => HttpResponse.json<RunSettingsResponse>({ model: 'gpt-6-luna', effort: 'low' })),
  http.get('/api/skills', () => HttpResponse.json([])),
  http.get('/api/settings', () =>
    HttpResponse.json<SettingsResponse>({ model: 'm', top_k: 4, uploads: uploadLimits }),
  ),
);
