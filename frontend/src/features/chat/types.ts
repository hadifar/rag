import type { ReasoningEvent, ReferencesEvent, TextEvent, TodosEvent, ToolEvent } from '@/shared/types';

// A bubble's content is the stream event it shows, minus its `type`.
export type TextContent = Omit<TextEvent, 'type'>;
export type ToolContent = Omit<ToolEvent, 'type'>;
export type TodosContent = Omit<TodosEvent, 'type'>;
export type ReferencesContent = Omit<ReferencesEvent, 'type'>;
// `streaming` until the model moves on from reasoning to answering or calling a tool.
export type ReasoningContent = Omit<ReasoningEvent, 'type'> & { streaming: boolean };

export type ChatMessageInput =
  | { type: 'typing' }
  | { type: 'text'; content: TextContent; position?: 'left' | 'right' }
  | { type: 'reasoning'; content: ReasoningContent }
  | { type: 'tool'; content: ToolContent }
  | { type: 'todos'; content: TodosContent }
  | { type: 'references'; content: ReferencesContent };

export type ChatMessage = ChatMessageInput & { id: string };
