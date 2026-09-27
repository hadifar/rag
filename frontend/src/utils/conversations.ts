import type { Schemas } from '../types';

export type Conversation = Schemas['ConversationResponse'];

/** Puts `conversation` first (it was just used), replacing any older copy of it. */
export function upsertConversation(list: Conversation[], conversation: Conversation): Conversation[] {
  return [conversation, ...list.filter((c) => c.id !== conversation.id)];
}

/**
 * Appends an older page. Conversations reorder while paging (using one moves it to
 * the top), so a row already shown can come back in a later page; keep the first.
 */
export function appendPage(list: Conversation[], page: Conversation[]): Conversation[] {
  const shown = new Set(list.map((c) => c.id));
  return [...list, ...page.filter((c) => !shown.has(c.id))];
}

export function renameConversation(list: Conversation[], id: string, title: string): Conversation[] {
  return list.map((c) => (c.id === id ? { ...c, title } : c));
}

export function removeConversation(list: Conversation[], id: string): Conversation[] {
  return list.filter((c) => c.id !== id);
}

export function conversationPath(id: string): string {
  return `/chat/${encodeURIComponent(id)}`;
}
