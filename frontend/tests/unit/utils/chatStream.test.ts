import { describe, expect, it, vi } from 'vitest';

import { assistantText, createBubbleHandler } from '../../../src/utils/chatStream';

function setup() {
  let nextId = 0;
  const append = vi.fn(() => `m${++nextId}`);
  const update = vi.fn();
  return { append, update, handle: createBubbleHandler(append, update) };
}

describe('createBubbleHandler', () => {
  it('grows one assistant bubble from text deltas', () => {
    const { append, update, handle } = setup();

    handle({ type: 'text', text: 'Hel' });
    handle({ type: 'text', text: 'lo' });

    expect(append).toHaveBeenCalledExactlyOnceWith(assistantText('Hel'));
    expect(update).toHaveBeenLastCalledWith('m1', assistantText('Hello'));
  });

  it('fills in the tool bubble when its result arrives', () => {
    const { append, update, handle } = setup();

    handle({ type: 'tool_start', name: 'search', query: 'pricing' });
    handle({ type: 'tool_result', name: 'search', output: '3 chunks' });

    expect(append).toHaveBeenCalledExactlyOnceWith({
      type: 'tool',
      content: { name: 'search', query: 'pricing', status: 'pending' },
    });
    expect(update).toHaveBeenCalledExactlyOnceWith('m1', {
      type: 'tool',
      content: { name: 'search', output: '3 chunks', status: 'done' },
    });
  });

  it('still shows a sources bubble when the search found nothing', () => {
    const { append, handle } = setup();

    handle({ type: 'sources', sources: [] });

    expect(append).toHaveBeenCalledExactlyOnceWith({ type: 'sources', content: { sources: [] } });
  });
});
