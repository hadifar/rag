import { useEffect, useRef, type MouseEvent, type ReactNode, type SyntheticEvent } from 'react';
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

/**
 * A centred card over a blurred backdrop; Escape, the backdrop and the X all close it. A
 * modal `<dialog>`: the browser keeps focus inside it and makes the page behind it inert.
 */
export function Modal({
  isOpen,
  onClose,
  labelledBy,
  describedBy,
  showCloseButton = true,
  className = '',
  children,
}: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!isOpen || !dialog) return;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const { overflow } = document.body.style;
    dialog.showModal();
    document.body.style.overflow = 'hidden';
    return () => {
      dialog.close();
      document.body.style.overflow = overflow;
      opener?.focus();
    };
  }, [isOpen]);

  // Escape: the dialog stays open until the parent closes it through `isOpen`.
  const handleCancel = (e: SyntheticEvent<HTMLDialogElement>) => {
    e.preventDefault();
    onClose();
  };

  // The card fills the dialog, so a click on the dialog itself is on its backdrop.
  const handleClick = (e: MouseEvent<HTMLDialogElement>) => {
    if (e.target === e.currentTarget) onClose();
  };

  if (!isOpen) return null;

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={labelledBy}
      aria-describedby={describedBy}
      onCancel={handleCancel}
      onClick={handleClick}
      className="m-auto w-full max-w-[min(28rem,calc(100%-2rem))] rounded-3xl bg-white p-0 shadow-2xl ring-1 ring-slate-900/5 transition duration-200 ease-out backdrop:bg-slate-900/40 backdrop:backdrop-blur-sm starting:scale-95 starting:opacity-0 motion-reduce:transition-none"
    >
      <div className={`relative p-6 sm:p-8 ${className}`}>
        {showCloseButton && (
          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            className="absolute top-4 right-4 flex size-9 items-center justify-center rounded-full bg-slate-100 text-slate-400 transition-colors hover:bg-slate-200 hover:text-slate-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500"
          >
            <XMarkIcon className="size-5" />
          </button>
        )}
        {children}
      </div>
    </dialog>
  );
}
