import type {
  ReasoningEvent,
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
// `streaming` until the model moves on from reasoning to answering or calling a tool.
export type ReasoningContent = Omit<ReasoningEvent, 'type'> & { streaming: boolean };
export type ErrorContent = { text: string };
// The ids of the knowledge-base sources among a turn's artifacts.
export type SourcesContent = { sources: string[] };

/** A file sent with a message, as its bubble shows it. */
export type AttachmentChip = { id: string; name: string; isImage: boolean };
// The user's message: its text (empty if they sent only files) and its attachments.
export type UserContent = TextContent & { attachments: AttachmentChip[] };

/** A file picked to send with the next message, while and after it uploads. */
export type AttachmentDraft = {
  /** Stable while it's in the composer. */
  key: string;
  name: string;
  /** A data URL of an image, to preview it; null for any other file (or until it's read). */
  previewUrl: string | null;
  status: 'uploading' | 'ready' | 'failed';
  /** Why it failed, fit to show. */
  error: string | null;
  /** Once uploaded: the attachment, and the conversation it went to. */
  attachment: AttachmentChip | null;
  conversationId: string | null;
};

/** One bubble of the chat; `id` is stable, so a bubble can be grown in place. */
export type Bubble = { id: string } & (
  | { type: 'user'; content: UserContent }
  | { type: 'text'; content: TextContent }
  | { type: 'reasoning'; content: ReasoningContent }
  | { type: 'tool'; content: ToolContent }
  | { type: 'todos'; content: TodosContent }
  | { type: 'verification'; content: VerificationContent }
  | { type: 'sources'; content: SourcesContent }
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

/** A skill the user can invoke with "/<name>" at the start of a message. */
export type SkillOption = { name: string; description: string };
