import type { TextContent } from '../types';
import { BubbleFrame } from './BubbleFrame';
import { MarkdownBody } from './MarkdownBody';

/** The assistant's answer, as markdown. */
export function TextBubble({ text }: TextContent) {
  return (
    <BubbleFrame className="leading-6 text-slate-800">
      <MarkdownBody text={text} />
    </BubbleFrame>
  );
}
