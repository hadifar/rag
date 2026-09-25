export type TextContent = { text: string };

export type ToolContent = {
  name: string;
  query?: string;
  output?: string;
  status: 'pending' | 'done';
};

export type SourcesContent = { names: string[] };

export type ChatMessageInput =
  | { type: 'typing' }
  | { type: 'text'; content: TextContent; position?: 'left' | 'right' }
  | { type: 'tool'; content: ToolContent }
  | { type: 'sources'; content: SourcesContent };

export type ChatMessage = ChatMessageInput & { id: string };

export type ChatStreamEvent =
  | { type: 'text'; text: string }
  | { type: 'tool_start'; name: string; query: string }
  | { type: 'tool_result'; name: string; output: string }
  | ({ type: 'sources' } & SourcesContent);
