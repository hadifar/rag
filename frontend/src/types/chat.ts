export type TextContent = { text: string };

export type ToolContent = {
  name: string;
  args?: Record<string, unknown>;
  output?: string;
  status: 'pending' | 'done';
};

export type SourcesContent = { names: string[] };

export type ChatStreamEvent =
  | { type: 'text'; text: string }
  | { type: 'tool_start'; name: string; args: Record<string, unknown> }
  | { type: 'tool_result'; name: string; output: string }
  | ({ type: 'sources' } & SourcesContent);
