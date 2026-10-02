import type { TextContent } from '../types';
import { BubbleFrame } from './BubbleFrame';

export function UserBubble({ text }: TextContent) {
  return (
    <BubbleFrame look="user">
      <p className="whitespace-pre-wrap leading-6 text-slate-800">{text}</p>
    </BubbleFrame>
  );
}
