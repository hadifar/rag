import { jsonPostInit, request, requestJson } from './client';
import type {
  ConversationPageResponse,
  ConversationResponse,
  HistoryMessageResponse,
} from '../types';

/** The user's empty conversation (new, or the one they already have); `generateTitle` names it. */
export function createConversation(signal?: AbortSignal): Promise<ConversationResponse> {
  return requestJson('conversations', { method: 'POST', signal });
}

/** Marks the conversation as just used, so the server lists it first; sent with each follow-up message. */
export async function touchConversation(id: string, signal?: AbortSignal): Promise<void> {
  await request(`conversations/${encodeURIComponent(id)}/touch`, { method: 'POST', signal });
}

/** Names the conversation from its first message (LLM-written, or cut from it if that fails); needs no answer. */
export function generateTitle(id: string, message: string): Promise<ConversationResponse> {
  return requestJson(`conversations/${encodeURIComponent(id)}/title`, jsonPostInit({ message }));
}

export function listConversations(
  cursor: string | null,
  signal?: AbortSignal
): Promise<ConversationPageResponse> {
  const query = cursor ? `?${new URLSearchParams({ cursor })}` : '';
  return requestJson(`conversations${query}`, { signal });
}

export function fetchConversationMessages(
  id: string,
  signal?: AbortSignal
): Promise<HistoryMessageResponse[]> {
  return requestJson(`conversations/${encodeURIComponent(id)}/messages`, { signal });
}

export async function deleteConversation(id: string): Promise<void> {
  await request(`conversations/${encodeURIComponent(id)}`, { method: 'DELETE' });
}
