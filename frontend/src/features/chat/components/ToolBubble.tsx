import { useState } from 'react';
import { ChevronRightIcon } from '@heroicons/react/24/outline';
import type { ToolContent } from '../types';
import { BubbleFrame } from './BubbleFrame';
import { MarkdownBody } from './MarkdownBody';

// `label` is missing from transcripts stored before the backend sent one.
export function ToolBubble({ name, label, output, status }: ToolContent) {
  const [collapsed, setCollapsed] = useState(true);
  const title = `🔧 ${label ?? name}`;
  const headerClass = 'flex w-full items-center gap-1.5 text-left text-xs font-medium text-slate-700';

  return (
    <BubbleFrame className={`w-[480px] ${status === 'pending' ? 'opacity-70' : ''}`}>
      {output ? (
        <button
          type="button"
          onClick={() => setCollapsed((prev) => !prev)}
          aria-expanded={!collapsed}
          className={headerClass}
        >
          <ChevronRightIcon
            className={`size-3.5 shrink-0 transition-transform ${collapsed ? '' : 'rotate-90'}`}
          />
          {title}
        </button>
      ) : (
        <div className={headerClass}>{title}</div>
      )}
      {output && !collapsed && (
        <div className="mt-1 box-border break-words rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-600">
          <MarkdownBody text={output} />
        </div>
      )}
    </BubbleFrame>
  );
}
