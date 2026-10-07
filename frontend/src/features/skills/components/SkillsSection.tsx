import { useRef, type ChangeEvent } from 'react';
import { TrashIcon } from '@heroicons/react/24/outline';

import { Button } from '@/shared/ui/Button';
import { ConfirmDeleteModal } from '@/shared/ui/ConfirmDeleteModal';
import { IconButton } from '@/shared/ui/IconButton';
import { StatusLine } from '@/shared/ui/StatusLine';
import { useSkillUpload } from '../hooks/useSkillUpload';
import { useSkills } from '../hooks/useSkills';
import { SKILL_ACCEPT } from '../model/skills';

/** The user's skills: listed with their descriptions, uploaded and deleted here. */
export function SkillsSection() {
  const { skills, status, pending, isDeleting, deleteError, requestDelete, confirm, cancel } =
    useSkills();
  const { upload, uploading, notice } = useSkillUpload();
  const fileInput = useRef<HTMLInputElement>(null);

  const handlePick = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) upload(file);
    // Picking the same file again still fires a change.
    e.target.value = '';
  };

  return (
    <section className="flex max-w-xl flex-col gap-3 border-t border-slate-200 p-8">
      <h2 className="m-0 text-base font-semibold text-slate-900">Skills</h2>
      <p className="m-0 text-sm text-slate-600">
        Instructions the assistant loads when a question fits their description. Upload a
        SKILL.md file with a <code>name</code> and <code>description</code> in its frontmatter.
      </p>

      {status === 'loading' && <StatusLine>Loading skills…</StatusLine>}
      {status === 'error' && <StatusLine tone="warning">Couldn't load your skills.</StatusLine>}
      {status === 'ready' && skills.length === 0 && <StatusLine>No skills yet.</StatusLine>}

      {skills.length > 0 && (
        <ul className="m-0 flex list-none flex-col divide-y divide-slate-200 rounded-xl border border-slate-200 p-0">
          {skills.map((skill) => (
            <li key={skill.id} className="flex items-start gap-3 px-4 py-3">
              <div className="min-w-0 flex-1">
                <p className="m-0 truncate font-mono text-sm text-slate-900">{skill.name}</p>
                <p className="m-0 mt-0.5 text-[13px] break-words text-slate-600">{skill.description}</p>
              </div>
              <IconButton label={`Delete ${skill.name}`} tone="danger" onClick={() => requestDelete(skill)}>
                <TrashIcon className="size-4" />
              </IconButton>
            </li>
          ))}
        </ul>
      )}

      <div className="flex items-center gap-3">
        <Button
          variant="secondary"
          onClick={() => fileInput.current?.click()}
          disabled={uploading}
          className="self-start"
        >
          {uploading ? 'Uploading…' : 'Upload skill'}
        </Button>
        <input
          ref={fileInput}
          type="file"
          accept={SKILL_ACCEPT}
          hidden
          aria-label="Skill file"
          onChange={handlePick}
        />
        {notice && (
          <StatusLine role="status" tone={notice.tone} size="sm">
            {notice.text}
          </StatusLine>
        )}
      </div>

      <ConfirmDeleteModal
        isOpen={pending !== null}
        title="Delete skill?"
        message={
          <>
            <span className="font-medium text-slate-700">“{pending?.name}”</span> will be permanently
            deleted. This can't be undone.
          </>
        }
        isBusy={isDeleting}
        error={deleteError}
        onConfirm={confirm}
        onCancel={cancel}
      />
    </section>
  );
}
