import type { InfiniteData } from '@tanstack/react-query';

import type { ConversationPageResponse, ConversationResponse } from '@/shared/types';

/** The sidebar list as it's cached: the pages loaded so far, each with its cursor. */
export type ConversationPages = InfiniteData<ConversationPageResponse, string | null>;

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

/** The loaded pages as one list, oldest page last, each conversation once. */
export function flattenPages(data: ConversationPages): ConversationResponse[] {
  return data.pages.reduce<ConversationResponse[]>((list, page) => appendPage(list, page.items), []);
}

/**
 * Applies `update` to the loaded pages as one list. The result goes in the first page and
 * the others are emptied, but every page keeps its cursor, so "load more" and a refetch
 * (which reloads each page by its cursor) still work.
 */
export function patchPages(
  data: ConversationPages,
  update: (list: ConversationResponse[]) => ConversationResponse[]
): ConversationPages {
  const list = update(flattenPages(data));
  return { ...data, pages: data.pages.map((page, i) => ({ ...page, items: i === 0 ? list : [] })) };
}
