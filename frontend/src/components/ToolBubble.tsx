import { useState } from 'react';
import type { ToolContent } from '../types/chat';

export function ToolBubble({ name, args, output, status }: ToolContent) {
  const [collapsed, setCollapsed] = useState(true);
  const query = typeof args?.query === 'string' ? args.query : JSON.stringify(args);

  return (
    <div className="tool-bubble" data-status={status}>
      <button
        type="button"
        className="tool-bubble-title"
        onClick={() => setCollapsed((prev) => !prev)}
        aria-expanded={!collapsed}
      >
        <span aria-hidden="true">{collapsed ? '▶' : '▼'}</span> 🔧 {name}
      </button>
      {!collapsed && (
        <div className="tool-bubble-body">
          {status === 'pending' ? `Searching for: ${query}` : output}
        </div>
      )}
    </div>
  );
}
