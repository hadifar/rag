import { useState } from 'react';

import { useKbUpload } from '../hooks/useKbUpload';
import { KbUploadModal } from './KbUploadModal';

/** Admin-only: shows how the last upload went, and opens the upload dialog. */
export function KnowledgeBaseSection() {
  const { phase, error, busy, summary, lastRunAt, lastRunStatus, upload, dismiss } =
    useKbUpload();
  const [open, setOpen] = useState(false);

  const close = () => {
    setOpen(false);
    dismiss();
  };

  return (
    <section className="flex max-w-xl flex-col gap-3 border-t border-slate-200 p-8">
      <h2 className="m-0 text-base font-semibold text-slate-900">Knowledge base</h2>

      {summary && lastRunAt ? (
        <p className="m-0 text-sm text-slate-600">
          Last upload ({lastRunAt}):{' '}
          <span className={lastRunStatus === 'failed' ? 'text-red-600' : undefined}>
            {summary}
          </span>
        </p>
      ) : (
        <p className="m-0 text-sm text-slate-500">Nothing uploaded from here yet.</p>
      )}

      <button
        type="button"
        onClick={() => setOpen(true)}
        className="self-start rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
      >
        {busy ? 'Show upload progress' : 'Upload knowledge base'}
      </button>

      {open && (
        <KbUploadModal
          phase={phase}
          busy={busy}
          error={error}
          summary={summary}
          onUpload={upload}
          onClose={close}
        />
      )}
    </section>
  );
}
