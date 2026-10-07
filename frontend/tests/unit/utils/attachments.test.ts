import { describe, expect, it } from 'vitest';

import { isUploading, readyAttachments, titleSource } from '@/features/chat/model/attachments';
import type { AttachmentDraft } from '@/features/chat/types';

function draft(status: AttachmentDraft['status'], id: string): AttachmentDraft {
  return {
    key: id,
    name: `${id}.md`,
    previewUrl: null,
    status,
    error: null,
    attachment: status === 'ready' ? { id, name: `${id}.md`, isImage: false } : null,
    conversationId: status === 'ready' ? 'c1' : null,
  };
}

describe('attachment drafts', () => {
  it('sends only the files that finished uploading', () => {
    const drafts = [draft('ready', 'a'), draft('failed', 'b'), draft('uploading', 'c')];

    expect(readyAttachments(drafts).map((a) => a.id)).toEqual(['a']);
    expect(isUploading(drafts)).toBe(true);
    expect(isUploading([draft('ready', 'a')])).toBe(false);
  });
});

describe('titleSource', () => {
  it('names a chat from its message, or from its files without one', () => {
    const files = [
      { id: 'a', name: 'notes.md', isImage: false },
      { id: 'b', name: 'error.png', isImage: true },
    ];

    expect(titleSource('How do I sync?', files)).toBe('How do I sync?');
    expect(titleSource('', files)).toBe('notes.md, error.png');
  });
});
