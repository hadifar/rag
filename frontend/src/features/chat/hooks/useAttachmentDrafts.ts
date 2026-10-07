import { useCallback, useState } from 'react';

import { createConversation } from '@/features/conversations';
import { errorDetail } from '@/shared/api/errors';
import type { ConversationResponse } from '@/shared/types';
import { discardAttachment, uploadAttachment } from '../api/attachments';
import {
  MAX_ATTACHMENTS,
  TOO_MANY_ATTACHMENTS,
  isImageFile,
  isUploading,
  readyAttachments,
  toChip,
} from '../model/attachments';
import type { AttachmentChip, AttachmentDraft } from '../types';
import { readAsDataUrl } from './dataUrl';

/**
 * The drafts, and which conversation's composer they're in (undefined: a new chat). A new
 * chat's files go to a conversation created for them: `created`.
 */
type Drafts = {
  conversationId: string | undefined;
  items: AttachmentDraft[];
  notice: string | null;
  created: ConversationResponse | null;
};

/** The files to send with a message; `conversation`, the new chat's, to send it to. */
export type TakenAttachments = { attachments: AttachmentChip[]; conversation: ConversationResponse | null };

const UPLOAD_FAILED = "Couldn't upload this file. Please try again.";
const NO_DRAFTS: AttachmentDraft[] = [];

function emptyDrafts(conversationId: string | undefined): Drafts {
  return { conversationId, items: [], notice: null, created: null };
}

/**
 * The files picked for the next message in the conversation on screen, each uploaded as
 * soon as it's picked. A new chat has no id yet: its files go to the user's empty
 * conversation, and its first message is sent there too (`take`). Leaving the
 * conversation drops them (the server prunes uploads that are never sent).
 */
export function useAttachmentDrafts(conversationId: string | undefined) {
  const [drafts, setDrafts] = useState<Drafts>(() => emptyDrafts(conversationId));
  // Another conversation's drafts don't follow the user to this one.
  const current = drafts.conversationId === conversationId ? drafts : null;
  const items = current?.items ?? NO_DRAFTS;

  // Updates the drafts of `forConversation`; a no-op once the user left it.
  const update = useCallback(
    (forConversation: string | undefined, change: (d: Drafts) => Drafts) => {
      setDrafts((d) => {
        return change(d.conversationId === forConversation ? d : emptyDrafts(forConversation));
      });
    },
    []
  );

  const edit = useCallback(
    (forConversation: string | undefined, key: string, patch: Partial<AttachmentDraft>) => {
      setDrafts((d) =>
        d.conversationId === forConversation
          ? { ...d, items: d.items.map((item) => (item.key === key ? { ...item, ...patch } : item)) }
          : d
      );
    },
    []
  );

  const upload = useCallback(
    async (forConversation: string | undefined, key: string, file: File) => {
      if (isImageFile(file)) {
        void readAsDataUrl(file)
          .then((previewUrl) => edit(forConversation, key, { previewUrl }))
          .catch(() => undefined);
      }
      try {
        let target = forConversation;
        if (target === undefined) {
          const created = await createConversation();
          // Only while the user is still in the new chat.
          setDrafts((d) => (d.conversationId === forConversation ? { ...d, created } : d));
          target = created.id;
        }
        const attachment = await uploadAttachment(target, file);
        edit(forConversation, key, { status: 'ready', attachment: toChip(attachment), conversationId: target });
      } catch (err) {
        edit(forConversation, key, { status: 'failed', error: errorDetail(err) ?? UPLOAD_FAILED });
      }
    },
    [edit]
  );

  const attach = useCallback(
    (files: File[]) => {
      const room = MAX_ATTACHMENTS - items.length;
      const picked = files.slice(0, Math.max(room, 0));
      const added = picked.map((file) => ({
        file,
        draft: {
          key: crypto.randomUUID(),
          name: file.name,
          previewUrl: null,
          status: 'uploading',
          error: null,
          attachment: null,
          conversationId: null,
        } satisfies AttachmentDraft,
      }));
      update(conversationId, (d) => ({
        ...d,
        items: [...d.items, ...added.map((a) => a.draft)],
        notice: files.length > picked.length ? TOO_MANY_ATTACHMENTS : null,
      }));
      for (const { file, draft } of added) void upload(conversationId, draft.key, file);
    },
    [conversationId, items.length, update, upload]
  );

  const remove = useCallback(
    (key: string) => {
      const removed = items.find((item) => item.key === key);
      update(conversationId, (d) => ({ ...d, items: d.items.filter((item) => item.key !== key), notice: null }));
      if (removed?.attachment && removed.conversationId) {
        // Best effort: one left behind is pruned once old.
        void discardAttachment(removed.conversationId, removed.attachment.id).catch(() => undefined);
      }
    },
    [conversationId, items, update]
  );

  // Hands over the uploaded files to send, and empties the composer's list. A new chat's
  // files name the conversation they're in, so its first message goes there too, even if
  // another tab has since taken the user's empty conversation.
  const take = useCallback((): TakenAttachments => {
    update(conversationId, () => emptyDrafts(conversationId));
    const attachments = readyAttachments(items);
    return { attachments, conversation: attachments.length > 0 ? (current?.created ?? null) : null };
  }, [conversationId, current, items, update]);

  return {
    drafts: items,
    notice: current?.notice ?? null,
    uploading: isUploading(items),
    hasReady: readyAttachments(items).length > 0,
    attach,
    remove,
    take,
  };
}
