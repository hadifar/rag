import type { AttachmentResponse } from '@/shared/types';
import type { AttachmentChip, AttachmentDraft } from '../types';

/** What the file picker offers; the backend decides by content (rag/services/attachment_service/kinds.py). */
export const ATTACHMENT_ACCEPT = '.md,.markdown,.png,.jpg,.jpeg';

// Keep in sync with MAX_ATTACHMENTS in rag/api/schema/conversation.py.
export const MAX_ATTACHMENTS = 3;

export const TOO_MANY_ATTACHMENTS = `You can attach up to ${MAX_ATTACHMENTS} files to a message.`;

export function toChip(attachment: AttachmentResponse): AttachmentChip {
  return {
    id: attachment.id,
    name: attachment.name,
    isImage: attachment.media_type.startsWith('image/'),
  };
}

/** Whether a picked file is an image, to preview it before it's uploaded. */
export function isImageFile(file: File): boolean {
  return file.type.startsWith('image/');
}

/** The drafts that uploaded, as the attachments to send. */
export function readyAttachments(drafts: AttachmentDraft[]): AttachmentChip[] {
  return drafts.flatMap((d) => (d.status === 'ready' && d.attachment ? [d.attachment] : []));
}

export function isUploading(drafts: AttachmentDraft[]): boolean {
  return drafts.some((d) => d.status === 'uploading');
}

/** What names a new chat: its first message, or the files sent without one. */
export function titleSource(text: string, attachments: AttachmentChip[]): string {
  return text || attachments.map((a) => a.name).join(', ');
}
