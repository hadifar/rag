import { describe, expect, it } from 'vitest';

import {
  flattenPages,
  patchPages,
  placeByRecency,
  replaceOrPrepend,
  upsertConversation,
  type ConversationPages,
} from '@/features/conversations/model/conversations';
import type { ConversationResponse } from '@/shared/types';

function conversation(id: string, updated_at = '2026-01-01T00:00:00Z'): ConversationResponse {
  return {
    id,
    title: id,
    created_at: '2026-01-01T00:00:00Z',
    updated_at,
    pinned_at: null,
    model: 'gpt-6-luna',
    effort: 'low',
  };
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

describe('placeByRecency', () => {
  const list = [conversation('a', '2026-01-03T00:00:00Z'), conversation('c', '2026-01-01T00:00:00Z')];

  it('slots an unpinned chat in where the server lists it', () => {
    const placed = placeByRecency(list, conversation('b', '2026-01-02T00:00:00Z'), true);

    expect(placed.map((c) => c.id)).toEqual(['a', 'b', 'c']);
  });

  it('breaks a tie on updated_at by the larger id first, as the server does', () => {
    const placed = placeByRecency(list, conversation('d', '2026-01-01T00:00:00Z'), true);

    expect(placed.map((c) => c.id)).toEqual(['a', 'd', 'c']);
  });

  it('leaves a chat older than every loaded row to a later page, if there is one', () => {
    const old = conversation('z', '2025-12-01T00:00:00Z');

    expect(placeByRecency(list, old, true).map((c) => c.id)).toEqual(['a', 'c']);
    expect(placeByRecency(list, old, false).map((c) => c.id)).toEqual(['a', 'c', 'z']);
  });

  it('replaces a listed chat in place', () => {
    const renamed = { ...conversation('c', '2026-01-01T00:00:00Z'), title: 'renamed' };

    expect(placeByRecency(list, renamed, true).map((c) => c.title)).toEqual(['a', 'renamed']);
  });
});

describe('replaceOrPrepend', () => {
  it('adds a newly pinned chat first, and replaces one already listed in place', () => {
    const list = [conversation('a'), conversation('b')];

    expect(replaceOrPrepend(list, conversation('c')).map((c) => c.id)).toEqual(['c', 'a', 'b']);
    const renamed = { ...conversation('b'), title: 'renamed' };
    expect(replaceOrPrepend(list, renamed).map((c) => c.title)).toEqual(['a', 'renamed']);
  });
});
