import { useEffect, useState, type SubmitEvent } from 'react';
import { ArrowPathIcon, XMarkIcon } from '@heroicons/react/24/outline';

import type { UploadPhase } from '../types';

type Props = {
  phase: UploadPhase;
  busy: boolean;
  error: string | null;
  summary: string | null;
  onUpload: (file: File) => void;
  onClose: () => void;
};

export function KbUploadModal({ phase, busy, error, summary, onUpload, onClose }: Props) {
  const [file, setFile] = useState<File | null>(null);

  // On the document, not the dialog: focus is often outside it (e.g. once the upload
  // button it was on unmounts).
  useEffect(() => {
    const closeOnEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', closeOnEscape);
    return () => document.removeEventListener('keydown', closeOnEscape);
  }, [onClose]);

  const handleSubmit = (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!file) return;
    onUpload(file);
    // The form unmounts while busy and comes back with an empty file input.
    setFile(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="kb-upload-title"
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"
      >
        <div className="mb-3 flex items-start justify-between gap-4">
          <h2 id="kb-upload-title" className="m-0 text-lg font-semibold text-slate-900">
            Upload knowledge base
          </h2>
          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          >
            <XMarkIcon className="size-5" />
          </button>
        </div>

        <p className="mt-0 mb-4 text-sm text-slate-600">
          A <code>.zip</code> of Markdown (<code>.md</code>) files. It replaces the current
          knowledge base: new and changed files are indexed, and files missing from the zip
          are removed.
        </p>

        {busy ? (
          <p role="status" className="m-0 flex items-center gap-2 text-sm text-slate-700">
            <ArrowPathIcon className="size-4 animate-spin text-indigo-600" />
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
            <button
              type="submit"
              disabled={!file}
              className="self-start rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-40"
            >
              Upload
            </button>
          </form>
        )}

        {phase === 'succeeded' && summary && (
          <p role="status" className="mt-4 mb-0 text-sm text-green-700">
            Done: {summary}
          </p>
        )}
        {phase === 'failed' && error && (
          <p role="alert" className="mt-4 mb-0 text-sm text-red-600">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}
