import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { ToolBubble } from '@/features/chat/components/ToolBubble';

describe('ToolBubble', () => {
  it('shows the label and expands to the output', async () => {
    const user = userEvent.setup();
    render(<ToolBubble name="search_kb" label="Searched: pricing" status="done" output="Plans start at $10" />);

    await user.click(screen.getByRole('button', { name: /Searched: pricing/ }));

    expect(screen.getByText('Plans start at $10')).toBeInTheDocument();
  });

  it('shows a call without output as a plain line', () => {
    render(<ToolBubble name="load_skill" label="Loaded skill: release-notes" status="done" />);

    expect(screen.getByText(/Loaded skill: release-notes/)).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('falls back to the name for a call stored without a label', () => {
    render(<ToolBubble name="search_kb" status="done" output="old" />);

    expect(screen.getByRole('button', { name: /search_kb/ })).toBeInTheDocument();
  });
});
