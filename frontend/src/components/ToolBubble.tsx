import type { ToolContent } from '../types/chat';

export function ToolBubble({ name, args, output, status }: ToolContent) {
  const query = typeof args?.query === 'string' ? args.query : JSON.stringify(args);

  return (
    <div className="tool-bubble" data-status={status}>
      <div className="tool-bubble-title">🔧 {name}</div>
      <div className="tool-bubble-body">
        {status === 'pending' ? `Searching for: ${query}` : output}
      </div>
    </div>
  );
}
