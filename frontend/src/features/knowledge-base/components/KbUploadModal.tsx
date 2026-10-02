import { useState, type SubmitEvent } from 'react';
import { ArrowPathIcon } from '@heroicons/react/24/outline';

import { Button } from '@/shared/ui/Button';
import { Modal } from '@/shared/ui/Modal';
import { StatusLine } from '@/shared/ui/StatusLine';
import type { UploadPhase } from '../types';

type Props = {
  phase: UploadPhase;
  busy: boolean;
  error: string | null;
  summary: string | null;
  onUpload: (file: File) => void;
  onClose: () => void;
};

/** Mounted only while open, so a reopened dialog starts with no file chosen. */
export function KbUploadModal({ phase, busy, error, summary, onUpload, onClose }: Props) {
  const [file, setFile] = useState<File | null>(null);

  const handleSubmit = (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!file) return;
    onUpload(file);
    // The form unmounts while busy and comes back with an empty file input.
    setFile(null);
  };

  return (
    <Modal isOpen onClose={onClose} labelledBy="kb-upload-title">
      {/* Clear of the close button in the corner. */}
      <h2 id="kb-upload-title" className="mt-0 mb-3 pr-10 text-lg font-semibold text-slate-900">
        Upload knowledge base
      </h2>

      <p className="mt-0 mb-4 text-sm text-slate-600">
        A <code>.zip</code> of Markdown (<code>.md</code>) files. It replaces the current
        knowledge base: new and changed files are indexed, and files missing from the zip
        are removed.
      </p>

      {busy ? (
        <p role="status" className="m-0 flex items-center gap-2 text-sm text-slate-700">
          <ArrowPathIcon className="size-4 animate-spin text-primary-600" />
          {phase === 'uploading'
            ? 'Uploading…'
            : 'Indexing… You can close this window; it keeps going on the server.'}
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            type="file"
            accept=".zip,application/zip"
            aria-label="Knowledge base zip"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="text-sm text-slate-700 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-medium file:text-slate-700 hover:file:bg-slate-200"
          />
          <Button type="submit" disabled={!file} className="self-start">
            Upload
          </Button>
        </form>
      )}

      {phase === 'succeeded' && summary && (
        <StatusLine tone="success" role="status" className="mt-4">
          Done: {summary}
        </StatusLine>
      )}
      {phase === 'failed' && error && (
        <StatusLine tone="error" role="alert" className="mt-4">
          {error}
        </StatusLine>
      )}
    </Modal>
  );
}
