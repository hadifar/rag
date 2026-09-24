export type TextContent = { text: string };

export type ToolContent = {
  name: string;
  query?: string;
  output?: string;
  status: 'pending' | 'done';
};

export type SourcesContent = { names: string[] };

export type ChatMessage =
  | { id: string; type: 'typing' }
  | { id: string; type: 'text'; content: TextContent; position?: 'left' | 'right' }
  | { id: string; type: 'tool'; content: ToolContent }
  | { id: string; type: 'sources'; content: SourcesContent };

// `Omit<Union, K>` collapses to the keys common to every branch, losing the
// discriminated union. This distributes it over each branch instead.
type DistributiveOmit<T, K extends PropertyKey> = T extends unknown ? Omit<T, K> : never;

export type ChatMessageInput = DistributiveOmit<ChatMessage, 'id'>;

export type ChatStreamEvent =
  | { type: 'text'; text: string }
  | { type: 'tool_start'; name: string; query: string }
  | { type: 'tool_result'; name: string; output: string }
  | ({ type: 'sources' } & SourcesContent);
