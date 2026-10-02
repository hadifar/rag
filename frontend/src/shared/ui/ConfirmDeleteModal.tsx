import type { ReactNode } from 'react';
import { ArrowPathIcon, TrashIcon } from '@heroicons/react/24/outline';

import { Modal } from './Modal';

type Props = {
  isOpen: boolean;
  title: string;
  message: ReactNode;
  confirmLabel?: string;
  busyLabel?: string;
  isBusy: boolean;
  error: string | null;
  onConfirm: () => void;
  onCancel: () => void;
};

/** Asks before something is deleted for good. Cancel has focus, so Enter is the safe choice. */
export function ConfirmDeleteModal({
  isOpen,
  title,
  message,
  confirmLabel = 'Delete',
  busyLabel = 'Deleting…',
  isBusy,
  error,
  onConfirm,
  onCancel,
}: Props) {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onCancel}
      labelledBy="confirm-delete-title"
      describedBy="confirm-delete-message"
      showCloseButton={false}
    >
      <div className="text-center">
        <div className="mx-auto flex size-14 items-center justify-center rounded-full bg-red-100 ring-8 ring-red-50">
          <TrashIcon className="size-6 text-red-600" />
        </div>

        <h2 id="confirm-delete-title" className="mt-6 mb-0 text-lg font-semibold text-slate-900">
          {title}
        </h2>
        <p
          id="confirm-delete-message"
          className="mt-2 mb-0 text-sm leading-6 break-words text-slate-500"
        >
          {message}
        </p>

        {error && (
          <p role="alert" className="mt-4 mb-0 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <div className="mt-7 grid grid-cols-2 gap-3">
          <button
            type="button"
            autoFocus
            onClick={onCancel}
            disabled={isBusy}
            className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 shadow-xs transition-colors hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isBusy}
            className="flex items-center justify-center gap-2 rounded-xl bg-red-600 px-4 py-2.5 text-sm font-medium text-white shadow-xs transition-colors hover:bg-red-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600 disabled:opacity-70"
          >
            {isBusy && <ArrowPathIcon className="size-4 animate-spin" />}
            {isBusy ? busyLabel : confirmLabel}
          </button>
        </div>
      </div>
    </Modal>
  );
}
