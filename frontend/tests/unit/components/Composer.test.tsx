import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { Composer } from '@/features/chat/components/Composer';

function renderComposer() {
  const onSend = vi.fn();
  render(<Composer onSend={onSend} />);
  return {
    onSend,
    user: userEvent.setup(),
    box: screen.getByPlaceholderText('Type a message...'),
    send: screen.getByRole('button'),
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
