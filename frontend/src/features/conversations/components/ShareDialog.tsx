import { ArrowPathIcon, CheckIcon, LinkIcon } from '@heroicons/react/24/outline';

import { Button } from '@/shared/ui/Button';
import { Input } from '@/shared/ui/Input';
import { Modal } from '@/shared/ui/Modal';
import { StatusLine } from '@/shared/ui/StatusLine';
import type { LoadStatus } from '@/shared/types';

type ShareDialogProps = {
  isOpen: boolean;
  title: string;
  status: LoadStatus;
  link: string | null;
  sharedOn: string | null;
  isSaving: boolean;
  isStopping: boolean;
  copied: boolean;
  error: string | null;
  onSave: () => void;
  onStop: () => void;
  onCopy: () => void;
  onClose: () => void;
};

/** A chat's public read-only link: create it, copy it, update its snapshot or take it down. */
export function ShareDialog({
  isOpen,
  title,
  status,
  link,
  sharedOn,
  isSaving,
  isStopping,
  copied,
  error,
  onSave,
  onStop,
  onCopy,
  onClose,
}: ShareDialogProps) {
  const isBusy = isSaving || isStopping;

  return (
    <Modal isOpen={isOpen} onClose={onClose} labelledBy="share-title" describedBy="share-message">
      <h2 id="share-title" className="m-0 pr-10 text-lg font-semibold text-slate-900">
        Share chat
      </h2>
      <p className="mt-1 mb-0 truncate text-sm font-medium text-slate-700" title={title}>
        {title}
      </p>

      {status === 'loading' && (
        <StatusLine size="sm" className="mt-5">
          Loading…
        </StatusLine>
      )}

      {status === 'ready' && !link && (
        <>
          <p id="share-message" className="mt-4 mb-0 text-sm leading-6 text-slate-500">
            Anyone with the link can read this chat as it is now, without signing in. Messages
            you send later aren't included unless you update the link.
          </p>
          <Button className="mt-6 w-full" onClick={onSave} disabled={isBusy}>
            {isSaving ? <ArrowPathIcon className="size-4 animate-spin" /> : <LinkIcon className="size-4" />}
            {isSaving ? 'Creating link…' : 'Create link'}
          </Button>
        </>
      )}

      {status === 'ready' && link && (
        <>
          <p id="share-message" className="mt-4 mb-0 text-sm leading-6 text-slate-500">
            Shared on {sharedOn}. Anyone with the link can read the chat up to then. Update the
            link to include newer messages.
          </p>
          <div className="mt-4 flex gap-2">
            <Input
              readOnly
              value={link}
              aria-label="Share link"
              onFocus={(e) => e.currentTarget.select()}
              className="min-w-0 flex-1"
            />
            <Button variant="secondary" onClick={onCopy}>
              {copied ? <CheckIcon className="size-4" /> : <LinkIcon className="size-4" />}
              {copied ? 'Copied' : 'Copy'}
            </Button>
          </div>
          <div className="mt-6 flex justify-between gap-3">
            <Button variant="ghost" onClick={onStop} disabled={isBusy}>
              {isStopping ? 'Stopping…' : 'Stop sharing'}
            </Button>
            <Button variant="secondary" onClick={onSave} disabled={isBusy}>
              {isSaving && <ArrowPathIcon className="size-4 animate-spin" />}
              {isSaving ? 'Updating…' : 'Update link'}
            </Button>
          </div>
        </>
      )}

      {error && (
        <p role="alert" className="mt-4 mb-0 rounded-xl bg-danger-50 px-3 py-2 text-sm text-danger-700">
          {error}
        </p>
      )}
    </Modal>
  );
}
