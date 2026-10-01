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

  it('fills in the tool bubble when it is done', () => {
    const { append, update, handle } = setup();

    handle({ type: 'tool', name: 'search', status: 'pending', query: 'pricing' });
    handle({ type: 'tool', name: 'search', status: 'done', output: '3 chunks' });

    expect(append).toHaveBeenCalledExactlyOnceWith({
      type: 'tool',
      content: { name: 'search', query: 'pricing', status: 'pending' },
    });
    expect(update).toHaveBeenCalledExactlyOnceWith('m1', {
      type: 'tool',
      content: { name: 'search', output: '3 chunks', status: 'done' },
    });
  });

  it('grows one reasoning bubble, and ends it when the answer starts', () => {
    const { append, update, handle } = setup();

    handle({ type: 'reasoning', text: 'Weigh' });
    handle({ type: 'reasoning', text: 'ing' });
    handle({ type: 'text', text: 'Answer' });

    expect(append).toHaveBeenNthCalledWith(1, {
      type: 'reasoning',
      content: { text: 'Weigh', streaming: true },
    });
    expect(update).toHaveBeenCalledWith('m1', {
      type: 'reasoning',
      content: { text: 'Weighing', streaming: false },
    });
    expect(append).toHaveBeenNthCalledWith(2, assistantText('Answer'));
  });

  it('starts a new reasoning bubble for reasoning that follows a tool call', () => {
    const { append, handle } = setup();

    handle({ type: 'reasoning', text: 'First' });
    handle({ type: 'tool', name: 'search', status: 'pending', query: 'pricing' });
    handle({ type: 'reasoning', text: 'Second' });

    expect(append).toHaveBeenNthCalledWith(3, {
      type: 'reasoning',
      content: { text: 'Second', streaming: true },
    });
  });

  it('still shows a references bubble when the search found nothing', () => {
    const { append, handle } = setup();

    handle({ type: 'references', references: [] });

    expect(append).toHaveBeenCalledExactlyOnceWith({ type: 'references', content: { references: [] } });
  });

  it('starts a new assistant bubble for text that follows a tool call', () => {
    const { append, update, handle } = setup();

    handle({ type: 'text', text: 'Let me check that...' });
    handle({ type: 'tool', name: 'search', status: 'pending', query: 'pricing' });
    handle({ type: 'tool', name: 'search', status: 'done', output: '3 chunks' });
    handle({ type: 'text', text: 'Here is the answer.' });

    // m1: first text bubble, m2: tool bubble, m3: a *new* text bubble — not a merge into m1.
    expect(append).toHaveBeenNthCalledWith(1, assistantText('Let me check that...'));
    expect(append).toHaveBeenNthCalledWith(3, assistantText('Here is the answer.'));
    expect(update).not.toHaveBeenCalledWith('m1', expect.anything());
  });

  it('matches pending/done tool events in the order the calls started', () => {
    const { append, update, handle } = setup();

    handle({ type: 'tool', name: 'search', status: 'pending', query: 'a' });
    handle({ type: 'tool', name: 'search', status: 'pending', query: 'b' });
    handle({ type: 'tool', name: 'search', status: 'done', output: 'result a' });
    handle({ type: 'tool', name: 'search', status: 'done', output: 'result b' });

    expect(append).toHaveBeenCalledTimes(2);
    expect(update).toHaveBeenNthCalledWith(1, 'm1', {
      type: 'tool',
      content: { name: 'search', output: 'result a', status: 'done' },
    });
    expect(update).toHaveBeenNthCalledWith(2, 'm2', {
      type: 'tool',
      content: { name: 'search', output: 'result b', status: 'done' },
    });
  });

  it('rewrites one plan bubble in place each time the plan changes', () => {
    const { append, update, handle } = setup();
    const first = [{ content: 'Find the note', status: 'in_progress' as const }];
    const second = [{ content: 'Find the note', status: 'completed' as const }];

    handle({ type: 'todos', todos: first });
    handle({ type: 'tool', name: 'search', status: 'pending', query: 'note' });
    handle({ type: 'todos', todos: second });

    expect(append).toHaveBeenNthCalledWith(1, { type: 'todos', content: { todos: first } });
    expect(update).toHaveBeenCalledExactlyOnceWith('m1', {
      type: 'todos',
      content: { todos: second },
    });
  });

  it('starts a new assistant bubble for text that follows the plan', () => {
    const { append, handle } = setup();

    handle({ type: 'text', text: 'Let me plan.' });
    handle({ type: 'todos', todos: [{ content: 'Find the note', status: 'pending' }] });
    handle({ type: 'text', text: 'Here is the answer.' });

    expect(append).toHaveBeenNthCalledWith(3, assistantText('Here is the answer.'));
  });
});
