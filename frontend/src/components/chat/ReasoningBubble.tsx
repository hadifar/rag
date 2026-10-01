import { useState } from 'react';
import Markdown from 'react-markdown';
import { ChevronRightIcon } from '@heroicons/react/24/outline';
import type { ReasoningContent } from '../../types';

// Open while the model reasons, closed once it moves on, unless the user has toggled it.
export function ReasoningBubble({ text, streaming }: ReasoningContent) {
  const [userOpen, setUserOpen] = useState<boolean | null>(null);
  const open = userOpen ?? streaming;

  return (
    <div className="max-w-[480px] px-3 text-sm">
      <button
        type="button"
        onClick={() => setUserOpen(!open)}
        aria-expanded={open}
        className={`flex items-center gap-1.5 text-slate-500 ${streaming ? 'animate-pulse' : ''}`}
      >
        <ChevronRightIcon
          className={`size-3.5 shrink-0 transition-transform ${open ? 'rotate-90' : ''}`}
        />
        {streaming ? 'Thinking…' : 'Thought process'}
      </button>
      {open && (
        <div className="mt-1 space-y-2 border-l-2 border-slate-200 pl-3 leading-6 text-slate-500">
          <Markdown>{text}</Markdown>
        </div>
      )}
    </div>
  );
}
