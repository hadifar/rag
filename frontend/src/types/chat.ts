import type { SourcesEvent, TextEvent, ToolEvent } from './api';

// A bubble's content is the stream event it shows, minus its `type`.
export type TextContent = Omit<TextEvent, 'type'>;
export type ToolContent = Omit<ToolEvent, 'type'>;
export type SourcesContent = Omit<SourcesEvent, 'type'>;

export type ChatMessageInput =
  | { type: 'typing' }
  | { type: 'text'; content: TextContent; position?: 'left' | 'right' }
  | { type: 'tool'; content: ToolContent }
  | { type: 'sources'; content: SourcesContent };

export type ChatMessage = ChatMessageInput & { id: string };
