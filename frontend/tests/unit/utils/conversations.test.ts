import { describe, expect, it } from 'vitest';

import {
  flattenPages,
  patchPages,
  upsertConversation,
  type ConversationPages,
} from '@/features/conversations/model/conversations';
import type { ConversationResponse } from '@/shared/types';

function conversation(id: string): ConversationResponse {
  return { id, title: id, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' };
}

const twoPages: ConversationPages = {
  pages: [
    { items: [conversation('a'), conversation('b')], next_cursor: 'c1' },
    { items: [conversation('b'), conversation('c')], next_cursor: 'c2' },
  ],
  pageParams: [null, 'c1'],
};

describe('flattenPages', () => {
  it('lists every page in order, keeping the first copy of a row that moved', () => {
    expect(flattenPages(twoPages).map((c) => c.id)).toEqual(['a', 'b', 'c']);
  });
});

describe('patchPages', () => {
  it('applies the update to the whole list and keeps every cursor', () => {
    const patched = patchPages(twoPages, (list) => upsertConversation(list, conversation('c')));

    expect(flattenPages(patched).map((c) => c.id)).toEqual(['c', 'a', 'b']);
    expect(patched.pages.map((p) => p.next_cursor)).toEqual(['c1', 'c2']);
    expect(patched.pageParams).toEqual([null, 'c1']);
  });
});
