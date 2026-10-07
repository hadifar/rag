import { api, unwrap } from '@/shared/api/client';
import type { AttachmentResponse } from '@/shared/types';

function byIds(conversationId: string, attachmentId: string) {
  return { path: { conversation_id: conversationId, attachment_id: attachmentId } };
}

/**
 * Uploads a file to the conversation, to send with a message by its id. A rejected file
 * throws an `ApiError` whose `detail` is the backend's reason (e.g. not a .md, .png or
 * .jpg, or too large), fit to show as is.
 */
export function uploadAttachment(conversationId: string, file: File): Promise<AttachmentResponse> {
  return unwrap(
    api.POST('/api/conversations/{conversation_id}/attachments', {
      params: { path: { conversation_id: conversationId } },
      // The schema types the file as a string; it goes as form data, which the
      // serializer builds from the File itself.
      body: { file: file.name },
      bodySerializer: () => {
        const form = new FormData();
        form.append('file', file);
        return form;
      },
    })
  );
}

export function fetchAttachment(
  conversationId: string,
  attachmentId: string,
  signal?: AbortSignal
): Promise<Blob> {
  return unwrap(
    api.GET('/api/conversations/{conversation_id}/attachments/{attachment_id}', {
      params: byIds(conversationId, attachmentId),
      parseAs: 'blob',
      signal,
    })
  );
}

/** Deletes an attachment that was never sent. */
export async function discardAttachment(conversationId: string, attachmentId: string): Promise<void> {
  await unwrap(
    api.DELETE('/api/conversations/{conversation_id}/attachments/{attachment_id}', {
      params: byIds(conversationId, attachmentId),
    })
  );
}
