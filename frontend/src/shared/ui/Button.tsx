import type { ComponentProps } from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost';
export type ButtonSize = 'md' | 'icon';

const base =
  'inline-flex shrink-0 items-center justify-center gap-2 rounded-xl text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50';

const variants: Record<ButtonVariant, string> = {
  primary:
    'bg-primary-600 text-white shadow-xs enabled:hover:bg-primary-700 focus-visible:outline-primary-500',
  secondary:
    'border border-slate-300 bg-white text-slate-700 shadow-xs enabled:hover:bg-slate-50 enabled:hover:text-slate-900 focus-visible:outline-primary-500',
  danger:
    'bg-danger-600 text-white shadow-xs enabled:hover:bg-danger-700 focus-visible:outline-danger-600',
  ghost:
    'text-slate-600 enabled:hover:bg-slate-100 enabled:hover:text-slate-900 focus-visible:outline-primary-500',
};

const sizes: Record<ButtonSize, string> = {
  md: 'px-4 py-2.5',
  icon: 'size-9',
};

type ButtonProps = ComponentProps<'button'> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
};

/**
 * The app's button. `className` is for layout only (margins, alignment, width): the look
 * comes from `variant` and `size`, so every button stays alike. Not a submit button
 * unless `type="submit"` says so.
 */
export function Button({
  variant = 'primary',
  size = 'md',
  type = 'button',
  className = '',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    />
  );
}
