import { useState } from 'react';
import { ChevronRightIcon } from '@heroicons/react/24/outline';
import type { ToolContent } from '../types';
import { BubbleFrame } from './BubbleFrame';
import { MarkdownBody } from './MarkdownBody';

export function ToolBubble({ name, query, output, status }: ToolContent) {
  const [collapsed, setCollapsed] = useState(true);

  return (
    <BubbleFrame look="card" className={status === 'pending' ? 'opacity-70' : ''}>
      <button
        type="button"
        onClick={() => setCollapsed((prev) => !prev)}
        aria-expanded={!collapsed}
        className="flex w-full items-center gap-1.5 text-left font-medium text-slate-700"
      >
        <ChevronRightIcon
          className={`size-3.5 shrink-0 transition-transform ${collapsed ? '' : 'rotate-90'}`}
        />
        🔧 {name}
      </button>
      {!collapsed && (
        <div className="mt-1 break-words text-slate-600">
          {status === 'pending' ? `Searching for: ${query ?? ''}` : <MarkdownBody text={output ?? ''} />}
        </div>
      )}
    </BubbleFrame>
  );
}
