import type { ComponentProps, ReactNode } from 'react';

// `box-border`: without Tailwind's preflight, boxes are content-box, and a full-width
// field's padding would push it past its container.
const inputCls =
  'box-border w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm font-normal text-slate-900 placeholder:text-slate-400 shadow-sm transition focus:border-transparent focus:outline-none focus:ring-2 focus:ring-primary-500';

/** The app's text input. `className` is for layout only (e.g. `flex-1`). */
export function Input({ className = '', ...props }: ComponentProps<'input'>) {
  return <input className={`${inputCls} ${className}`} {...props} />;
}

type TextFieldProps = ComponentProps<'input'> & { label: ReactNode };

/** An `Input` with its label above it. */
export function TextField({ label, ...props }: TextFieldProps) {
  return (
    <label className="flex flex-col gap-1.5 text-sm font-medium text-slate-700">
      {label}
      <Input {...props} />
    </label>
  );
}
