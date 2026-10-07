import { useCallback, useRef, useState, type ReactNode } from 'react';
import { ChevronDownIcon } from '@heroicons/react/24/outline';

import { Dropdown } from '@/shared/ui/Dropdown';

type RunPickerProps = {
  /** The button's accessible name, e.g. "Model: gpt-6-luna". */
  label: string;
  /** What the button shows: the current choice. */
  value: string;
  /** `DropdownOption`s, one per choice. */
  children: ReactNode;
};

/** A small button showing the current choice, which opens the menu of choices. */
export function RunPicker({ label, value, children }: RunPickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const close = useCallback(() => setIsOpen(false), []);
  const button = useRef<HTMLButtonElement>(null);

  return (
    <>
      <button
        ref={button}
        type="button"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((open) => !open)}
        className="flex h-9 shrink-0 items-center gap-1 rounded-lg px-2 text-xs font-medium text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 focus-visible:outline-2 focus-visible:outline-primary-500"
      >
        {value}
        <ChevronDownIcon className="size-3" />
      </button>
      <Dropdown isOpen={isOpen} onClose={close} anchorRef={button} label={label}>
        {children}
      </Dropdown>
    </>
  );
}
