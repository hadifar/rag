import { useState } from 'react';

import { Button } from '@/shared/ui/Button';
import { StatusLine } from '@/shared/ui/StatusLine';
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
          <span className={lastRunStatus === 'failed' ? 'text-danger-600' : undefined}>
            {summary}
          </span>
        </p>
      ) : (
        <StatusLine>Nothing uploaded from here yet.</StatusLine>
      )}

      <Button variant="secondary" onClick={() => setOpen(true)} className="self-start">
        {busy ? 'Show upload progress' : 'Upload knowledge base'}
      </Button>

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
