import { useEffect, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { XMarkIcon } from '@heroicons/react/24/outline';

type Props = {
  isOpen: boolean;
  onClose: () => void;
  /** Id of the element that names the dialog, for screen readers. */
  labelledBy: string;
  describedBy?: string;
  showCloseButton?: boolean;
  className?: string;
  children: ReactNode;
};

/** A centred card over a blurred backdrop; Escape, the backdrop and the X all close it. */
export function Modal({
  isOpen,
  onClose,
  labelledBy,
  describedBy,
  showCloseButton = true,
  className = '',
  children,
}: Props) {
  // On the document, not the dialog: focus isn't always inside it.
  useEffect(() => {
    if (!isOpen) return;
    const closeOnEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', closeOnEscape);
    return () => document.removeEventListener('keydown', closeOnEscape);
  }, [isOpen, onClose]);

  // Separate from the Escape listener so a new onClose doesn't re-run it and steal focus.
  useEffect(() => {
    if (!isOpen) return;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const { overflow } = document.body.style;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = overflow;
      opener?.focus();
    };
  }, [isOpen]);

  if (!isOpen) return null;

  // Portalled so a parent's overflow or stacking context can't clip it.
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto p-4">
      <div
        aria-hidden="true"
        onClick={onClose}
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity duration-200 starting:opacity-0 motion-reduce:transition-none"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        aria-describedby={describedBy}
        className={`relative w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl ring-1 ring-slate-900/5 transition duration-200 ease-out starting:scale-95 starting:opacity-0 motion-reduce:transition-none sm:p-8 ${className}`}
      >
        {showCloseButton && (
          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            className="absolute top-4 right-4 flex size-9 items-center justify-center rounded-full bg-slate-100 text-slate-400 transition-colors hover:bg-slate-200 hover:text-slate-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500"
          >
            <XMarkIcon className="size-5" />
          </button>
        )}
        {children}
      </div>
    </div>,
    document.body
  );
}
