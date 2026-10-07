import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { Composer, type ComposerAttachments } from '@/features/chat/components/Composer';
import type { AttachmentDraft } from '@/features/chat/types';

function renderComposer() {
  const onSend = vi.fn();
  render(<Composer onSend={onSend} />);
  return {
    onSend,
    user: userEvent.setup(),
    box: screen.getByPlaceholderText('Type a message...'),
    send: screen.getByRole('button', { name: 'Send' }),
  };
}

describe('Composer', () => {
  it('sends the trimmed text on Enter and clears the box', async () => {
    const { onSend, user, box } = renderComposer();

    await user.type(box, '  hi there  {Enter}');

    expect(onSend).toHaveBeenCalledExactlyOnceWith('hi there');
    expect(box).toHaveValue('');
  });

  it('adds a new line on Shift+Enter instead of sending', async () => {
    const { onSend, user, box } = renderComposer();

    await user.type(box, 'line 1{Shift>}{Enter}{/Shift}line 2');

    expect(onSend).not.toHaveBeenCalled();
    expect(box).toHaveValue('line 1\nline 2');
  });

  it('only enables the send button once there is text', async () => {
    const { onSend, user, box, send } = renderComposer();
    expect(send).toBeDisabled();

    await user.type(box, '   ');
    expect(send).toBeDisabled();

    await user.type(box, 'hello');
    await user.click(send);
    expect(onSend).toHaveBeenCalledExactlyOnceWith('hello');
  });
});

describe('Composer attachments', () => {
  const notes = new File(['# Notes'], 'notes.md', { type: 'text/markdown' });

  function attachments(overrides: Partial<ComposerAttachments> = {}): ComposerAttachments {
    return {
      drafts: [],
      notice: null,
      uploading: false,
      hasReady: false,
      onAttach: vi.fn(),
      onRemove: vi.fn(),
      ...overrides,
    };
  }

  function draft(status: AttachmentDraft['status'], error: string | null = null): AttachmentDraft {
    return {
      key: 'k1',
      name: 'notes.md',
      previewUrl: null,
      status,
      error,
      attachment: status === 'ready' ? { id: 'a1', name: 'notes.md', isImage: false } : null,
      conversationId: status === 'ready' ? 'c1' : null,
    };
  }

  it('attaches the files picked with the + button', async () => {
    const files = attachments();
    render(<Composer onSend={vi.fn()} attachments={files} />);
    const user = userEvent.setup();

    expect(screen.getByRole('button', { name: 'Attach files' })).toBeInTheDocument();
    await user.upload(screen.getByTestId('attachment-input'), notes);

    expect(files.onAttach).toHaveBeenCalledExactlyOnceWith([notes]);
  });

  it('attaches a pasted file instead of typing it', async () => {
    const files = attachments();
    render(<Composer onSend={vi.fn()} attachments={files} />);
    const user = userEvent.setup();

    await user.click(screen.getByPlaceholderText('Type a message...'));
    await user.paste({ files: [notes] } as unknown as DataTransfer);

    expect(files.onAttach).toHaveBeenCalledExactlyOnceWith([notes]);
  });

  it('sends a message of only its uploaded files', async () => {
    const onSend = vi.fn();
    render(<Composer onSend={onSend} attachments={attachments({ drafts: [draft('ready')], hasReady: true })} />);

    await userEvent.setup().click(screen.getByRole('button', { name: 'Send' }));

    expect(onSend).toHaveBeenCalledExactlyOnceWith('');
  });

  it('waits for the files to upload before sending', async () => {
    const onSend = vi.fn();
    render(
      <Composer
        onSend={onSend}
        attachments={attachments({ drafts: [draft('uploading')], uploading: true, hasReady: false })}
      />
    );
    const user = userEvent.setup();

    await user.type(screen.getByPlaceholderText('Type a message...'), 'hi{Enter}');

    expect(screen.getByText('Uploading…')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled();
    expect(onSend).not.toHaveBeenCalled();
  });

  it('shows why a file failed, and removes it', async () => {
    const files = attachments({ drafts: [draft('failed', 'Only .md, .png, .jpg files can be attached')] });
    render(<Composer onSend={vi.fn()} attachments={files} />);

    expect(screen.getByRole('alert')).toHaveTextContent('Only .md, .png, .jpg files can be attached');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Remove notes.md' }));

    expect(files.onRemove).toHaveBeenCalledExactlyOnceWith('k1');
  });
});
