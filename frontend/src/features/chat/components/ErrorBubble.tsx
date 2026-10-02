import type { ErrorContent } from '../types';
import { BubbleFrame } from './BubbleFrame';

/** Why an answer or a conversation couldn't be shown; reads like an assistant reply. */
export function ErrorBubble({ text }: ErrorContent) {
  return (
    <BubbleFrame className="leading-6 text-slate-800">
      <p className="whitespace-pre-wrap">{text}</p>
    </BubbleFrame>
  );
}
