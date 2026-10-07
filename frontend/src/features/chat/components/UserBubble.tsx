import type { UserContent } from '../types';
import { SentAttachments } from './AttachmentChips';
import { BubbleFrame } from './BubbleFrame';

type UserBubbleProps = UserContent & {
  /** The chat it's in, to show its images; left out (a shared chat), files show by name. */
  conversationId?: string;
};

export function UserBubble({ text, attachments, conversationId }: UserBubbleProps) {
  return (
    <BubbleFrame look="user" className="space-y-2">
      {attachments.length > 0 && <SentAttachments attachments={attachments} conversationId={conversationId} />}
      {text && <p className="whitespace-pre-wrap leading-6 text-slate-800">{text}</p>}
    </BubbleFrame>
  );
}
