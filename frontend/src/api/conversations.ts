import { ApiError, apiUrl, authHeader } from './base';
import type { Schemas } from '../types';

async function parseJson<T>(res: Response, what: string): Promise<T> {
  if (!res.ok) {
    throw new ApiError(res.status, `failed to ${what}: ${res.status}`);
  }
  return res.json();
}

export function listConversations(
  accessToken: string,
  cursor: string | null
): Promise<Schemas['ConversationPageResponse']> {
  const query = cursor ? `?${new URLSearchParams({ cursor })}` : '';
  return fetch(apiUrl(`conversations${query}`), { headers: authHeader(accessToken) }).then(
    (res) => parseJson(res, 'load conversations')
  );
}

export function fetchConversationMessages(
  id: string,
  accessToken: string,
  signal?: AbortSignal
): Promise<Schemas['HistoryMessageResponse'][]> {
  return fetch(apiUrl(`conversations/${encodeURIComponent(id)}/messages`), {
    headers: authHeader(accessToken),
    signal,
  }).then((res) => parseJson(res, 'load conversation'));
}

export async function deleteConversation(id: string, accessToken: string): Promise<void> {
  const res = await fetch(apiUrl(`conversations/${encodeURIComponent(id)}`), {
    method: 'DELETE',
    headers: authHeader(accessToken),
  });
  if (!res.ok) {
    throw new ApiError(res.status, `failed to delete conversation: ${res.status}`);
  }
}
