import { ShieldCheckIcon } from '@heroicons/react/24/outline';
import type { AnswerCheckContent } from '../types';
import { BubbleFrame } from './BubbleFrame';

// One line, light like the thought process: the check of the answer against its sources.
export function AnswerCheckBubble({ status, grounded }: AnswerCheckContent) {
  const pending = status === 'pending';

  return (
    <BubbleFrame>
      <div className={`flex items-center gap-1.5 text-slate-400 ${pending ? 'animate-pulse' : ''}`}>
        <ShieldCheckIcon className="size-3.5 shrink-0" />
        {pending ? 'Verifying sources…' : grounded ? 'Sources verified' : 'Not supported by the sources, rewriting'}
      </div>
    </BubbleFrame>
  );
}
