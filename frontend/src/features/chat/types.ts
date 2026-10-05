import type {
  ReasoningEvent,
  ReferencesEvent,
  TextEvent,
  TodosEvent,
  ToolEvent,
  VerificationEvent,
} from '@/shared/types';

// A bubble's content is the stream event it shows, minus its `type`.
export type TextContent = Omit<TextEvent, 'type'>;
export type ToolContent = Omit<ToolEvent, 'type'>;
export type TodosContent = Omit<TodosEvent, 'type'>;
export type VerificationContent = Omit<VerificationEvent, 'type'>;
export type ReferencesContent = Omit<ReferencesEvent, 'type'>;
// `streaming` until the model moves on from reasoning to answering or calling a tool.
export type ReasoningContent = Omit<ReasoningEvent, 'type'> & { streaming: boolean };
export type ErrorContent = { text: string };

/** One bubble of the chat; `id` is stable, so a bubble can be grown in place. */
export type Bubble = { id: string } & (
  | { type: 'user'; content: TextContent }
  | { type: 'text'; content: TextContent }
  | { type: 'reasoning'; content: ReasoningContent }
  | { type: 'tool'; content: ToolContent }
  | { type: 'todos'; content: TodosContent }
  | { type: 'verification'; content: VerificationContent }
  | { type: 'references'; content: ReferencesContent }
  | { type: 'error'; content: ErrorContent }
);

export type BubbleType = Bubble['type'];

/** The bubble of type `K`. */
export type BubbleOf<K extends BubbleType> = Extract<Bubble, { type: K }>;

/** Which bubbles the answer being streamed grows next. */
export type Turn = {
  textId: string | null;
  reasoningId: string | null;
  // FIFO: the backend doesn't send a call id, so this assumes tool calls resolve in the
  // order they started. True for the common case (one call, or calls that don't race);
  // genuinely concurrent calls need a call id from the backend to track precisely.
  pendingToolIds: string[];
  todosId: string | null;
  verificationId: string | null;
};

/** A conversation as shown: its bubbles, and the answer still being streamed, if any. */
export type Transcript = {
  bubbles: Bubble[];
  turn: Turn | null;
  /** The id the next bubble gets. */
  nextId: number;
};
