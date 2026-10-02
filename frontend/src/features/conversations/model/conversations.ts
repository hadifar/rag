import type { ConversationResponse } from '@/shared/types';

/** Puts `conversation` first (it was just used), replacing any older copy of it. */
export function upsertConversation(
  list: ConversationResponse[],
  conversation: ConversationResponse
): ConversationResponse[] {
  return [conversation, ...list.filter((c) => c.id !== conversation.id)];
}

/** Moves the conversation with `id` to the top (it was just used), if it's listed. */
export function moveToTop(list: ConversationResponse[], id: string): ConversationResponse[] {
  const conversation = list.find((c) => c.id === id);
  return conversation ? upsertConversation(list, conversation) : list;
}

/**
 * Appends an older page. Conversations reorder while paging (using one moves it to
 * the top), so a row already shown can come back in a later page; keep the first.
 */
export function appendPage(
  list: ConversationResponse[],
  page: ConversationResponse[]
): ConversationResponse[] {
  const shown = new Set(list.map((c) => c.id));
  return [...list, ...page.filter((c) => !shown.has(c.id))];
}

export function renameConversation(
  list: ConversationResponse[],
  id: string,
  title: string
): ConversationResponse[] {
  return list.map((c) => (c.id === id ? { ...c, title } : c));
}

export function removeConversation(
  list: ConversationResponse[],
  id: string
): ConversationResponse[] {
  return list.filter((c) => c.id !== id);
}

export function conversationPath(id: string): string {
  return `/chat/${encodeURIComponent(id)}`;
}
