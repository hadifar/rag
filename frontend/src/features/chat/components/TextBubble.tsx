import { CheckIcon, ClipboardIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import { IconButton } from '@/shared/ui/IconButton';
import { type CopyState, useCopyText } from '../hooks/useCopyText';
import type { TextContent } from '../types';
import { BubbleFrame } from './BubbleFrame';
import { MarkdownBody } from './MarkdownBody';

const COPY_LABEL: Record<CopyState, string> = {
  idle: 'Copy answer',
  copied: 'Copied',
  failed: 'Copy failed',
};

const COPY_ICON: Record<CopyState, typeof ClipboardIcon> = {
  idle: ClipboardIcon,
  copied: CheckIcon,
  failed: ExclamationTriangleIcon,
};

/** The assistant's answer, as markdown, with a button to copy it as written. */
export function TextBubble({ text }: TextContent) {
  const { state, copy } = useCopyText(text);
  const Icon = COPY_ICON[state];
  return (
    <BubbleFrame look="answer" className="relative pr-9 leading-6 text-slate-800">
      <IconButton label={COPY_LABEL[state]} onClick={copy} className="absolute top-1.5 right-1.5">
        <Icon className="size-4" />
      </IconButton>
      <MarkdownBody text={text} />
    </BubbleFrame>
  );
}
