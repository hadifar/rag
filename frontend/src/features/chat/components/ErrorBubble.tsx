import type { ErrorContent } from '../types';

/** Why an answer or a conversation couldn't be shown; reads like an assistant reply. */
export function ErrorBubble({ text }: ErrorContent) {
  return (
    <div className="max-w-[480px] px-3 text-sm leading-6 text-slate-800">
      <p className="whitespace-pre-wrap">{text}</p>
    </div>
  );
}
