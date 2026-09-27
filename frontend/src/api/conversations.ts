import { ApiError, apiUrl, authFetch } from './client';
import type { Schemas } from '../types';

async function parseJson<T>(res: Response, what: string): Promise<T> {
  if (!res.ok) {
    throw new ApiError(res.status, `failed to ${what}: ${res.status}`);
  }
  return res.json();
}

export function listConversations(
  cursor: string | null
): Promise<Schemas['ConversationPageResponse']> {
  const query = cursor ? `?${new URLSearchParams({ cursor })}` : '';
  return authFetch(apiUrl(`conversations${query}`)).then((res) =>
    parseJson(res, 'load conversations')
  );
}

export function fetchConversationMessages(
  id: string,
  signal?: AbortSignal
): Promise<Schemas['HistoryMessageResponse'][]> {
  return authFetch(apiUrl(`conversations/${encodeURIComponent(id)}/messages`), {
    signal,
  }).then((res) => parseJson(res, 'load conversation'));
}

export async function deleteConversation(id: string): Promise<void> {
  const res = await authFetch(apiUrl(`conversations/${encodeURIComponent(id)}`), {
    method: 'DELETE',
  });
  if (!res.ok) {
    throw new ApiError(res.status, `failed to delete conversation: ${res.status}`);
  }
}
