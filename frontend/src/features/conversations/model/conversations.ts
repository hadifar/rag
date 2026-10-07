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

/** True if `a` lists above `b` among the recent ones: used later, or the larger id on a tie. */
function isNewer(a: ConversationResponse, b: ConversationResponse): boolean {
  const diff = Date.parse(a.updated_at) - Date.parse(b.updated_at);
  return diff !== 0 ? diff > 0 : a.id > b.id;
}

/**
 * Puts `conversation` among the recent ones where the server lists them, replacing any
 * older copy in place. If it's older than every row loaded and more pages exist, it's
 * left out: a later page brings it.
 */
export function placeByRecency(
  list: ConversationResponse[],
  conversation: ConversationResponse,
  hasMore: boolean
): ConversationResponse[] {
  if (list.some((c) => c.id === conversation.id)) {
    return list.map((c) => (c.id === conversation.id ? conversation : c));
  }
  const at = list.findIndex((c) => isNewer(conversation, c));
  if (at === -1) return hasMore ? list : [...list, conversation];
  return [...list.slice(0, at), conversation, ...list.slice(at)];
}

/** Replaces the conversation in place if it's listed, else adds it first (just pinned). */
export function replaceOrPrepend(
  list: ConversationResponse[],
  conversation: ConversationResponse
): ConversationResponse[] {
  return list.some((c) => c.id === conversation.id)
    ? list.map((c) => (c.id === conversation.id ? conversation : c))
    : [conversation, ...list];
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

/** True if the server has older conversations than the pages loaded so far. */
export function hasMorePages(data: ConversationPages): boolean {
  return data.pages.at(-1)?.next_cursor != null;
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
