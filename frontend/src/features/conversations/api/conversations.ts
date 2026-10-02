import { api, unwrap } from '@/shared/api/client';
import type {
  ConversationPageResponse,
  ConversationResponse,
  HistoryMessageResponse,
} from '@/shared/types';

const byId = (id: string) => ({ path: { conversation_id: id } });

/** The user's empty conversation (new, or the one they already have); `generateTitle` names it. */
export function createConversation(signal?: AbortSignal): Promise<ConversationResponse> {
  return unwrap(api.POST('/api/conversations', { signal }));
}

/** Marks the conversation as just used, so the server lists it first; sent with each follow-up message. */
export async function touchConversation(id: string, signal?: AbortSignal): Promise<void> {
  await unwrap(api.POST('/api/conversations/{conversation_id}/touch', { params: byId(id), signal }));
}

/** Names the conversation from its first message (LLM-written, or cut from it if that fails); needs no answer. */
export function generateTitle(id: string, message: string): Promise<ConversationResponse> {
  return unwrap(
    api.POST('/api/conversations/{conversation_id}/title', { params: byId(id), body: { message } })
  );
}

export function listConversations(
  cursor: string | null,
  signal?: AbortSignal
): Promise<ConversationPageResponse> {
  return unwrap(api.GET('/api/conversations', { params: { query: cursor ? { cursor } : {} }, signal }));
}

export function fetchConversationMessages(
  id: string,
  signal?: AbortSignal
): Promise<HistoryMessageResponse[]> {
  return unwrap(api.GET('/api/conversations/{conversation_id}/messages', { params: byId(id), signal }));
}

export async function deleteConversation(id: string): Promise<void> {
  await unwrap(api.DELETE('/api/conversations/{conversation_id}', { params: byId(id) }));
}
