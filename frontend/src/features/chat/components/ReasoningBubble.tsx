import { useState } from 'react';
import Markdown from 'react-markdown';
import { ChevronRightIcon } from '@heroicons/react/24/outline';
import type { ReasoningContent } from '../types';
import { BubbleFrame } from './BubbleFrame';

// Shown in full, lighter than the answer so it reads as an aside; the user can fold it.
export function ReasoningBubble({ text, streaming }: ReasoningContent) {
  const [open, setOpen] = useState(true);

  return (
    <BubbleFrame>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        className={`flex items-center gap-1.5 text-slate-400 ${streaming ? 'animate-pulse' : ''}`}
      >
        <ChevronRightIcon
          className={`size-3.5 shrink-0 transition-transform ${open ? 'rotate-90' : ''}`}
        />
        {streaming ? 'Thinking…' : 'Thought process'}
      </button>
      {open && (
        <div className="mt-1 space-y-2 border-l-2 border-slate-100 pl-3 leading-6 text-slate-400">
          <Markdown>{text}</Markdown>
        </div>
      )}
    </BubbleFrame>
  );
}
