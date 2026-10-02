import type { ReactNode } from 'react';

const looks = {
  /** Flush text, like the assistant's answer. */
  plain: 'px-3',
  /** A tinted card, for asides such as a tool call or the sources. */
  card: 'rounded-xl bg-slate-50 px-3 py-2',
  /** The user's own message. */
  user: 'rounded-2xl rounded-tr-sm bg-slate-100 px-4 py-3',
};

type BubbleFrameProps = {
  look?: keyof typeof looks;
  /** Extra classes for this bubble's own text or state (e.g. dimmed while pending). */
  className?: string;
  children: ReactNode;
};

/** The box every chat bubble sits in: one width, one text size, a `look` per kind. */
export function BubbleFrame({ look = 'plain', className = '', children }: BubbleFrameProps) {
  return <div className={`max-w-[480px] text-sm ${looks[look]} ${className}`}>{children}</div>;
}
