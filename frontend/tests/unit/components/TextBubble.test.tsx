import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { TextBubble } from '@/features/chat/components/TextBubble';

describe('TextBubble', () => {
  it('copies the answer as raw markdown and says so', async () => {
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue();
    render(<TextBubble text={'**Bold** and a list:\n\n- one'} />);

    await user.click(screen.getByRole('button', { name: 'Copy answer' }));

    expect(writeText).toHaveBeenCalledExactlyOnceWith('**Bold** and a list:\n\n- one');
    expect(await screen.findByRole('button', { name: 'Copied' })).toBeInTheDocument();
  });

  it('says when the copy failed', async () => {
    const user = userEvent.setup();
    vi.spyOn(navigator.clipboard, 'writeText').mockRejectedValue(new Error('denied'));
    render(<TextBubble text="hi" />);

    await user.click(screen.getByRole('button', { name: 'Copy answer' }));

    expect(await screen.findByRole('button', { name: 'Copy failed' })).toBeInTheDocument();
  });
});
