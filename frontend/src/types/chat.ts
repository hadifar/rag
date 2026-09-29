import type { Schemas } from './api';

// A bubble's content is the stream event it shows, minus its `type`.
export type TextContent = Omit<Schemas['TextEvent'], 'type'>;
export type ToolContent = Omit<Schemas['ToolEvent'], 'type'>;
export type SourcesContent = Omit<Schemas['SourcesEvent'], 'type'>;

export type ChatMessageInput =
  | { type: 'typing' }
  | { type: 'text'; content: TextContent; position?: 'left' | 'right' }
  | { type: 'tool'; content: ToolContent }
  | { type: 'sources'; content: SourcesContent };

export type ChatMessage = ChatMessageInput & { id: string };

/** One event of a message's answer stream; the shapes come from the backend's schema. */
export type ChatStreamEvent =
  | Schemas['TextEvent']
  | Schemas['ToolEvent']
  | Schemas['SourcesEvent'];
