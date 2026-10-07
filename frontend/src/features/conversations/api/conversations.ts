import { api, unwrap } from '@/shared/api/client';
import type {
  ConversationPageResponse,
  ConversationResponse,
  ConversationUpdateRequest,
  HistoryMessageResponse,
  ShareResponse,
} from '@/shared/types';

const byId = (id: string) => ({ path: { conversation_id: id } });

/** The user's empty conversation (new, or the one they already have); `generateTitle` names it. */
export function createConversation(signal?: AbortSignal): Promise<ConversationResponse> {
  return unwrap(api.POST('/api/conversations', { signal }));
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

/** The pinned conversations, last pinned first; `listConversations` lists the rest. */
export function listPinnedConversations(signal?: AbortSignal): Promise<ConversationResponse[]> {
  return unwrap(api.GET('/api/conversations/pinned', { signal }));
}

/** Renames, pins or unpins it; a field left out stays as is. */
export function updateConversation(
  id: string,
  body: ConversationUpdateRequest
): Promise<ConversationResponse> {
  return unwrap(api.PATCH('/api/conversations/{conversation_id}', { params: byId(id), body }));
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

/** Its public link, or null if it isn't shared. */
export function fetchShare(id: string, signal?: AbortSignal): Promise<ShareResponse | null> {
  return unwrap(api.GET('/api/conversations/{conversation_id}/share', { params: byId(id), signal }));
}

/** Shares it as it is now; sharing again updates what the same link shows. */
export function shareConversation(id: string): Promise<ShareResponse> {
  return unwrap(api.PUT('/api/conversations/{conversation_id}/share', { params: byId(id) }));
}

export async function unshareConversation(id: string): Promise<void> {
  await unwrap(api.DELETE('/api/conversations/{conversation_id}/share', { params: byId(id) }));
}
