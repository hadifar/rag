import { describe, expect, it } from 'vitest';

import {
  applyEvent,
  applyEvents,
  emptyTranscript,
  endTurn,
  fromHistory,
  isWaiting,
  startTurn,
} from '@/features/chat/model/transcript';
import type { StreamEventResponse } from '@/shared/types';

/** The bubbles one answer's events make, without their ids. */
function bubbles(events: StreamEventResponse[]) {
  return applyEvents(emptyTranscript(), events).bubbles.map(({ type, content }) => ({ type, content }));
}

describe('applyEvent', () => {
  it('grows one assistant bubble from text deltas', () => {
    expect(bubbles([
      { type: 'text', text: 'Hel' },
      { type: 'text', text: 'lo' },
    ])).toEqual([{ type: 'text', content: { text: 'Hello' } }]);
  });

  it('fills in the tool bubble when it is done', () => {
    expect(bubbles([
      { type: 'tool', name: 'search', status: 'pending', query: 'pricing' },
      { type: 'tool', name: 'search', status: 'done', output: '3 chunks' },
    ])).toEqual([{ type: 'tool', content: { name: 'search', output: '3 chunks', status: 'done' } }]);
  });

  it('grows one reasoning bubble, and ends it when the answer starts', () => {
    const reasoning = applyEvents(emptyTranscript(), [
      { type: 'reasoning', text: 'Weigh' },
      { type: 'reasoning', text: 'ing' },
    ]);
    expect(reasoning.bubbles).toMatchObject([
      { type: 'reasoning', content: { text: 'Weighing', streaming: true } },
    ]);

    expect(applyEvent(reasoning, { type: 'text', text: 'Answer' }).bubbles).toMatchObject([
      { type: 'reasoning', content: { text: 'Weighing', streaming: false } },
      { type: 'text', content: { text: 'Answer' } },
    ]);
  });

  it('starts a new reasoning bubble for reasoning that follows a tool call', () => {
    expect(bubbles([
      { type: 'reasoning', text: 'First' },
      { type: 'tool', name: 'search', status: 'pending', query: 'pricing' },
      { type: 'reasoning', text: 'Second' },
    ]).map((b) => b.type)).toEqual(['reasoning', 'tool', 'reasoning']);
  });

  it('still shows a references bubble when the search found nothing', () => {
    expect(bubbles([{ type: 'references', references: [] }])).toEqual([
      { type: 'references', content: { references: [] } },
    ]);
  });

  it('starts a new assistant bubble for text that follows a tool call', () => {
    expect(bubbles([
      { type: 'text', text: 'Let me check that...' },
      { type: 'tool', name: 'search', status: 'pending', query: 'pricing' },
      { type: 'tool', name: 'search', status: 'done', output: '3 chunks' },
      { type: 'text', text: 'Here is the answer.' },
    ])).toMatchObject([
      { type: 'text', content: { text: 'Let me check that...' } },
      { type: 'tool' },
      { type: 'text', content: { text: 'Here is the answer.' } },
    ]);
  });

  it('matches pending/done tool events in the order the calls started', () => {
    expect(bubbles([
      { type: 'tool', name: 'search', status: 'pending', query: 'a' },
      { type: 'tool', name: 'search', status: 'pending', query: 'b' },
      { type: 'tool', name: 'search', status: 'done', output: 'result a' },
      { type: 'tool', name: 'search', status: 'done', output: 'result b' },
    ])).toMatchObject([
      { type: 'tool', content: { output: 'result a' } },
      { type: 'tool', content: { output: 'result b' } },
    ]);
  });

  it('rewrites one plan bubble in place each time the plan changes', () => {
    const first = [{ content: 'Find the note', status: 'in_progress' as const }];
    const second = [{ content: 'Find the note', status: 'completed' as const }];

    expect(bubbles([
      { type: 'todos', todos: first },
      { type: 'tool', name: 'search', status: 'pending', query: 'note' },
      { type: 'todos', todos: second },
    ])).toMatchObject([{ type: 'todos', content: { todos: second } }, { type: 'tool' }]);
  });

  it('starts a new assistant bubble for text that follows the plan', () => {
    expect(bubbles([
      { type: 'text', text: 'Let me plan.' },
      { type: 'todos', todos: [{ content: 'Find the note', status: 'pending' }] },
      { type: 'text', text: 'Here is the answer.' },
    ]).map((b) => b.type)).toEqual(['text', 'todos', 'text']);
  });

  it('fills in the verification bubble with its verdict, and shows the answer below it', () => {
    expect(bubbles([
      { type: 'verification', status: 'pending' },
      { type: 'verification', status: 'done', grounded: true },
      { type: 'text', text: 'It costs 10.' },
    ])).toEqual([
      { type: 'verification', content: { status: 'done', grounded: true } },
      { type: 'text', content: { text: 'It costs 10.' } },
    ]);
  });

  it('starts a new bubble for an answer checked after earlier text', () => {
    expect(bubbles([
      { type: 'text', text: 'Let me check.' },
      { type: 'verification', status: 'pending' },
      { type: 'verification', status: 'done', grounded: true },
      { type: 'text', text: 'It costs 10.' },
    ]).map((b) => b.type)).toEqual(['text', 'verification', 'text']);
  });

  it('shows a revision below the verdict that rejected the answer', () => {
    expect(bubbles([
      { type: 'verification', status: 'pending' },
      { type: 'verification', status: 'done', grounded: false },
      { type: 'text', text: 'revised' },
    ])).toEqual([
      { type: 'verification', content: { status: 'done', grounded: false } },
      { type: 'text', content: { text: 'revised' } },
    ]);
  });

  it('leaves the bubbles it did not change as they were', () => {
    const before = applyEvents(emptyTranscript(), [
      { type: 'tool', name: 'search', status: 'pending', query: 'a' },
      { type: 'text', text: 'Hel' },
    ]);
    const after = applyEvent(before, { type: 'text', text: 'lo' });

    expect(after.bubbles[0]).toBe(before.bubbles[0]);
    expect(after.bubbles[1]).not.toBe(before.bubbles[1]);
    expect(before.bubbles[1]).toMatchObject({ content: { text: 'Hel' } });
  });
});

describe('turns', () => {
  it('shows typing from the message until the answer ends', () => {
    const asked = startTurn(emptyTranscript(), 'Hi');
    expect(asked.bubbles).toMatchObject([{ type: 'user', content: { text: 'Hi' } }]);
    expect(isWaiting(asked)).toBe(true);

    const answering = applyEvents(asked, [
      { type: 'tool', name: 'search', status: 'pending', query: 'a' },
      { type: 'tool', name: 'search', status: 'done', output: '3 chunks' },
      { type: 'text', text: 'Hello' },
    ]);
    expect(isWaiting(answering)).toBe(true);
    expect(isWaiting(endTurn(answering))).toBe(false);
  });

  it('ends with an error bubble, and stops a reasoning bubble from streaming', () => {
    const thinking = applyEvent(startTurn(emptyTranscript(), 'Hi'), { type: 'reasoning', text: 'Hm' });

    const ended = endTurn(thinking, 'Something went wrong: offline');

    expect(ended.turn).toBeNull();
    expect(ended.bubbles).toMatchObject([
      { type: 'user' },
      { type: 'reasoning', content: { streaming: false } },
      { type: 'error', content: { text: 'Something went wrong: offline' } },
    ]);
  });

  it('gives every bubble its own id across turns', () => {
    const t = applyEvent(startTurn(applyEvent(startTurn(emptyTranscript(), 'a'), { type: 'text', text: 'x' }), 'b'), {
      type: 'text',
      text: 'y',
    });
    const ids = t.bubbles.map((b) => b.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});

describe('fromHistory', () => {
  it('replays each answer as the live stream showed it, each one closed', () => {
    const t = fromHistory([
      { role: 'user', text: 'Q1' },
      { role: 'assistant', events: [{ type: 'reasoning', text: 'R' }] },
      { role: 'user', text: 'Q2' },
      { role: 'assistant', events: [{ type: 'text', text: 'A2' }] },
    ]);

    expect(t.turn).toBeNull();
    expect(t.bubbles).toMatchObject([
      { type: 'user', content: { text: 'Q1' } },
      { type: 'reasoning', content: { text: 'R', streaming: false } },
      { type: 'user', content: { text: 'Q2' } },
      { type: 'text', content: { text: 'A2' } },
    ]);
  });
});
