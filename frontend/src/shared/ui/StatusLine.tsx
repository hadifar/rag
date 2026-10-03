import type { AriaRole, ReactNode } from 'react';

export type StatusTone = 'muted' | 'warning' | 'error' | 'success';

const tones: Record<StatusTone, string> = {
  muted: 'text-slate-500',
  warning: 'text-warning-600',
  error: 'text-danger-600',
  success: 'text-success-600',
};

const sizes = {
  md: 'text-sm',
  sm: 'text-[13px]',
};

type StatusLineProps = {
  tone?: StatusTone;
  size?: keyof typeof sizes;
  /** `status` or `alert` when a screen reader should announce it. */
  role?: AriaRole;
  /** For layout only (margins, padding). */
  className?: string;
  children: ReactNode;
};

/** One line on how something stands: loading, empty, saved, or what went wrong. */
export function StatusLine({ tone = 'muted', size = 'md', role, className = '', children }: StatusLineProps) {
  return (
    <p role={role} className={`m-0 ${sizes[size]} ${tones[tone]} ${className}`}>
      {children}
    </p>
  );
}
