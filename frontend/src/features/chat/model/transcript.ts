import type { HistoryMessageResponse, StreamEventResponse } from '@/shared/types';
import type { Bubble, BubbleOf, BubbleType, Transcript, Turn } from '../types';

// Every function here is pure: it returns a new transcript and leaves the old one as it
// was. A bubble that didn't change keeps its identity, so only changed bubbles re-render.

type NewBubble = Bubble extends infer B ? (B extends Bubble ? Omit<B, 'id'> : never) : never;

export function emptyTranscript(): Transcript {
  return { bubbles: [], turn: null, nextId: 0 };
}

function openTurn(): Turn {
  return { textId: null, reasoningId: null, pendingToolIds: [], todosId: null, verificationId: null };
}

/** A working copy that the functions below edit in place before handing it back. */
function draft(t: Transcript): Transcript {
  return { ...t, bubbles: [...t.bubbles], turn: t.turn && { ...t.turn, pendingToolIds: [...t.turn.pendingToolIds] } };
}

function push(t: Transcript, bubble: NewBubble): string {
  const id = String(t.nextId++);
  t.bubbles.push({ ...bubble, id } as Bubble);
  return id;
}

/** Replaces the content of bubble `id`, if it is still a `type` bubble. */
function edit<K extends BubbleType>(
  t: Transcript,
  id: string,
  type: K,
  content: (current: BubbleOf<K>['content']) => BubbleOf<K>['content']
): void {
  const i = t.bubbles.findIndex((b) => b.id === id);
  const bubble = t.bubbles[i];
  if (bubble?.type !== type) return;
  t.bubbles[i] = { ...bubble, content: content(bubble.content as BubbleOf<K>['content']) } as Bubble;
}

// More reasoning after anything else (say, after a tool call) starts a new bubble.
function endReasoning(t: Transcript, turn: Turn): void {
  if (turn.reasoningId === null) return;
  edit(t, turn.reasoningId, 'reasoning', (c) => ({ ...c, streaming: false }));
  turn.reasoningId = null;
}

/**
 * One streamed event into the answer's bubbles: text deltas grow a single assistant
 * bubble, reasoning deltas a single reasoning bubble (until the model answers or calls a
 * tool), a tool's bubble is filled in when it's `done`, the plan is one bubble rewritten
 * in place each time the agent updates it, the answer's check is a bubble filled in with
 * its verdict, and references get their own. A checked answer arrives only after its
 * verdict, so it follows the verification bubble.
 */
export function applyEvent(transcript: Transcript, event: StreamEventResponse): Transcript {
  const t = draft(transcript);
  const turn = t.turn ?? openTurn();
  t.turn = turn;

  if (event.type === 'reasoning') {
    if (turn.reasoningId === null) {
      turn.reasoningId = push(t, { type: 'reasoning', content: { text: event.text, streaming: true } });
    } else {
      edit(t, turn.reasoningId, 'reasoning', (c) => ({ ...c, text: c.text + event.text }));
    }
    return t;
  }
  endReasoning(t, turn);

  switch (event.type) {
    case 'text':
      if (turn.textId === null) {
        turn.textId = push(t, { type: 'text', content: { text: event.text } });
      } else {
        edit(t, turn.textId, 'text', (c) => ({ text: c.text + event.text }));
      }
      break;
    case 'tool': {
      const { type, ...content } = event;
      if (content.status === 'pending') {
        turn.pendingToolIds.push(push(t, { type, content }));
        // Further text after a tool call starts a new bubble, so reading order stays
        // text → tool → text instead of the later text merging into the earlier bubble.
        turn.textId = null;
      } else {
        const toolId = turn.pendingToolIds.shift();
        if (toolId !== undefined) edit(t, toolId, 'tool', () => content);
      }
      break;
    }
    case 'todos': {
      const { type, ...content } = event;
      if (turn.todosId === null) {
        turn.todosId = push(t, { type, content });
        // Like a tool call: later text goes below the plan, not into a bubble above it.
        turn.textId = null;
      } else {
        edit(t, turn.todosId, 'todos', () => content);
      }
      break;
    }
    case 'verification': {
      const { type, ...content } = event;
      if (content.status === 'pending') {
        turn.verificationId = push(t, { type, content });
        // Like a tool call: the checked answer is sent after its verdict, below it.
        turn.textId = null;
      } else if (turn.verificationId !== null) {
        edit(t, turn.verificationId, 'verification', () => content);
        turn.verificationId = null;
      }
      break;
    }
    case 'references':
      // Sent only when the answer searched; an empty list still gets its bubble.
      push(t, { type: 'references', content: { references: event.references } });
      break;
    case 'error':
      // The turn's last event: it failed, and says so where its answer would have been.
      push(t, { type: 'error', content: { text: event.message } });
      turn.textId = null;
      break;
    default:
      // A new backend event type fails to compile here until it's handled.
      event satisfies never;
  }
  return t;
}

export function applyEvents(t: Transcript, events: StreamEventResponse[]): Transcript {
  return events.reduce(applyEvent, t);
}

/**
 * Closes the answer being streamed, if any, with `error` shown after it. A tool call
 * still pending then never finished (its turn failed), so it stops showing as running.
 */
export function endTurn(transcript: Transcript, error?: string): Transcript {
  const t = draft(transcript);
  if (t.turn) {
    endReasoning(t, t.turn);
    for (const id of t.turn.pendingToolIds) {
      edit(t, id, 'tool', (c) => ({ ...c, status: 'done', output: "Didn't finish." }));
    }
  }
  t.turn = null;
  if (error !== undefined) push(t, { type: 'error', content: { text: error } });
  return t;
}

/** The user's message, and an answer opened for it (shown as typing until it ends). */
export function startTurn(transcript: Transcript, text: string): Transcript {
  const t = draft(endTurn(transcript));
  push(t, { type: 'user', content: { text } });
  t.turn = openTurn();
  return t;
}

/**
 * The failed answer that can be asked for again: the last bubble, if it's an error after
 * a question, and the question to send again. None while an answer is open.
 */
export function retryable(t: Transcript): { bubbleId: string; question: string } | null {
  const last = t.bubbles.at(-1);
  if (t.turn !== null || last?.type !== 'error') return null;
  const question = t.bubbles.findLast((b) => b.type === 'user');
  return question?.type === 'user' ? { bubbleId: last.id, question: question.content.text } : null;
}

/** Whether the assistant shows as typing: for as long as an answer is open. */
export function isWaiting(t: Transcript): boolean {
  return t.turn !== null;
}

/**
 * A saved conversation as the bubbles the live chat showed for it: each answer's events
 * are replayed through the same reducer the stream uses.
 */
export function fromHistory(history: HistoryMessageResponse[]): Transcript {
  return history.reduce((t, message) => {
    if (message.role === 'user') {
      const next = draft(t);
      push(next, { type: 'user', content: { text: message.text } });
      return next;
    }
    return endTurn(applyEvents(t, message.events));
  }, emptyTranscript());
}

/** A transcript that only says `text`, e.g. why a conversation couldn't load. */
export function errorTranscript(text: string): Transcript {
  return endTurn(emptyTranscript(), text);
}
