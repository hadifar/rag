import type { ReferencesEvent, TextEvent, ToolEvent } from './api';

// A bubble's content is the stream event it shows, minus its `type`.
export type TextContent = Omit<TextEvent, 'type'>;
export type ToolContent = Omit<ToolEvent, 'type'>;
export type ReferencesContent = Omit<ReferencesEvent, 'type'>;

export type ChatMessageInput =
  | { type: 'typing' }
  | { type: 'text'; content: TextContent; position?: 'left' | 'right' }
  | { type: 'tool'; content: ToolContent }
  | { type: 'references'; content: ReferencesContent };

export type ChatMessage = ChatMessageInput & { id: string };
