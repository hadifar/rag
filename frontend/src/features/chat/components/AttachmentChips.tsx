import { DocumentTextIcon, ExclamationCircleIcon, PhotoIcon, XMarkIcon } from '@heroicons/react/24/outline';

import { IconButton } from '@/shared/ui/IconButton';
import { useAttachmentUrl } from '../hooks/useAttachmentUrl';
import type { AttachmentChip, AttachmentDraft } from '../types';

function FileName({ name, isImage }: { name: string; isImage: boolean }) {
  const Icon = isImage ? PhotoIcon : DocumentTextIcon;
  return (
    // flex, not inline-flex: an inline box grows to fit the whole name, so it never truncates.
    <span className="flex min-w-0 items-center gap-1.5 text-xs text-slate-700">
      <Icon className="size-4 shrink-0 text-slate-500" aria-hidden />
      <span className="truncate">{name}</span>
    </span>
  );
}

/** The files picked for the next message: each uploading, ready, or why it failed. */
export function DraftAttachments({
  drafts,
  onRemove,
}: {
  drafts: AttachmentDraft[];
  onRemove: (key: string) => void;
}) {
  return (
    <ul aria-label="Attachments" className="m-0 flex list-none flex-wrap gap-2 p-0 px-1 pb-2">
      {drafts.map((draft) => (
        <li
          key={draft.key}
          className={`flex max-w-[180px] items-center gap-1.5 rounded-md border py-0.5 pr-0.5 pl-1.5 ${
            draft.status === 'failed' ? 'border-danger-200 bg-danger-50' : 'border-slate-200 bg-slate-50'
          }`}
        >
          {draft.previewUrl ? (
            <img src={draft.previewUrl} alt="" className="size-6 shrink-0 rounded object-cover" />
          ) : null}
          <div className="min-w-0 flex-1">
            <FileName name={draft.name} isImage={draft.previewUrl !== null} />
            {draft.status === 'uploading' && <p className="m-0 text-[11px] text-slate-500">Uploading…</p>}
            {draft.status === 'failed' && (
              <p role="alert" className="m-0 flex items-center gap-1 text-[11px] text-danger-700">
                <ExclamationCircleIcon className="size-3.5 shrink-0" aria-hidden />
                {draft.error}
              </p>
            )}
          </div>
          <IconButton label={`Remove ${draft.name}`} onClick={() => onRemove(draft.key)}>
            <XMarkIcon className="size-3.5" />
          </IconButton>
        </li>
      ))}
    </ul>
  );
}

function SentImage({ conversationId, attachment }: { conversationId: string; attachment: AttachmentChip }) {
  const url = useAttachmentUrl(conversationId, attachment.id);
  if (!url) return <FileName name={attachment.name} isImage />;
  return <img src={url} alt={attachment.name} className="max-h-48 max-w-full rounded-lg object-contain" />;
}

/**
 * A sent message's files. With `conversationId` (the owner's own chat) images show;
 * without it (a shared chat) every file shows by name only.
 */
export function SentAttachments({
  attachments,
  conversationId,
}: {
  attachments: AttachmentChip[];
  conversationId?: string;
}) {
  return (
    <ul aria-label="Attachments" className="m-0 flex list-none flex-col items-end gap-2 p-0">
      {attachments.map((attachment) => (
        <li key={attachment.id} className="max-w-full">
          {attachment.isImage && conversationId ? (
            <SentImage conversationId={conversationId} attachment={attachment} />
          ) : (
            <FileName name={attachment.name} isImage={attachment.isImage} />
          )}
        </li>
      ))}
    </ul>
  );
}
