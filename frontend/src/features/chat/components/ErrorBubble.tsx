import { ArrowPathIcon } from '@heroicons/react/24/outline';
import type { ErrorContent } from '../types';
import { BubbleFrame } from './BubbleFrame';

type ErrorBubbleProps = ErrorContent & {
  /** Asks the failed question again; only given while that's possible. */
  onRetry?: () => void;
};

/** Why an answer or a conversation couldn't be shown; reads like an assistant reply. */
export function ErrorBubble({ text, onRetry }: ErrorBubbleProps) {
  return (
    <BubbleFrame className="leading-6 text-slate-800">
      <p className="whitespace-pre-wrap">{text}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-1 inline-flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-slate-800"
        >
          <ArrowPathIcon className="size-3.5" />
          Retry
        </button>
      )}
    </BubbleFrame>
  );
}
