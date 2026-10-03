import type { ComponentProps } from 'react';

type IconButtonProps = Omit<ComponentProps<'button'>, 'aria-label' | 'title'> & {
  /** What it does, e.g. "Delete chat": its accessible name and tooltip. */
  label: string;
  /** `danger` turns red on hover, for a destructive action. */
  tone?: 'neutral' | 'danger';
};

const tones = {
  neutral: 'hover:text-slate-700',
  danger: 'hover:text-danger-600',
};

/** A small, quiet button showing only an icon (its `children`). `className` is for layout only. */
export function IconButton({
  label,
  tone = 'neutral',
  type = 'button',
  className = '',
  ...props
}: IconButtonProps) {
  return (
    <button
      type={type}
      aria-label={label}
      title={label}
      className={`shrink-0 rounded-md p-1 text-slate-400 transition-colors hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-primary-500 ${tones[tone]} ${className}`}
      {...props}
    />
  );
}
