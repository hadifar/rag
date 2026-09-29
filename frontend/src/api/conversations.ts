import { request, requestJson } from './client';
import type { Schemas } from '../types';

/** The user's empty conversation (new, or the one they already have); its first message names it. */
export function createConversation(signal?: AbortSignal): Promise<Schemas['ConversationResponse']> {
  return requestJson('conversations', { method: 'POST', signal });
}

export function listConversations(
  cursor: string | null
): Promise<Schemas['ConversationPageResponse']> {
  const query = cursor ? `?${new URLSearchParams({ cursor })}` : '';
  return requestJson(`conversations${query}`);
}

export function fetchConversationMessages(
  id: string,
  signal?: AbortSignal
): Promise<Schemas['HistoryMessageResponse'][]> {
  return requestJson(`conversations/${encodeURIComponent(id)}/messages`, { signal });
}

export async function deleteConversation(id: string): Promise<void> {
  await request(`conversations/${encodeURIComponent(id)}`, { method: 'DELETE' });
}
