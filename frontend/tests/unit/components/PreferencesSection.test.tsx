import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { PreferencesSection } from '@/features/preferences';
import type { PreferenceRequest, PreferenceResponse } from '@/shared/types';
import { server } from '../../server';

const URL = '/api/settings/preferences';

/** A fake preferences API over `saved`, with the server's duplicate and cap rules. */
function serve(saved: PreferenceResponse[], { full = false } = {}) {
  server.use(
    http.get(URL, () => HttpResponse.json(saved)),
    http.post(URL, async ({ request }) => {
      if (full) return new HttpResponse(null, { status: 409 });
      const { text } = (await request.json()) as PreferenceRequest;
      const existing = saved.find((p) => p.text.toLowerCase() === text.toLowerCase());
      if (existing) return HttpResponse.json(existing);
      const preference = { id: `id-${saved.length}`, text };
      saved.push(preference);
      return HttpResponse.json(preference);
    }),
    http.delete(`${URL}/:id`, ({ params }) => {
      const index = saved.findIndex((p) => p.id === params.id);
      if (index === -1) return new HttpResponse(null, { status: 404 });
      saved.splice(index, 1);
      return new HttpResponse(null, { status: 204 });
    })
  );
}

function renderSection() {
  render(<PreferencesSection />);
  return {
    user: userEvent.setup(),
    box: screen.getByRole('textbox', { name: 'New preference' }),
    addButton: screen.getByRole('button', { name: 'Add' }),
  };
}

describe('PreferencesSection', () => {
  it('lists the saved preferences', async () => {
    serve([{ id: 'a', text: 'Answer in Dutch' }]);
    renderSection();

    expect(await screen.findByText('Answer in Dutch')).toBeInTheDocument();
  });

  it('adds a preference and clears the box', async () => {
    serve([]);
    const { user, box } = renderSection();
    await screen.findByText('No preferences yet.');

    await user.type(box, '  Keep it short {Enter}');

    expect(await screen.findByText('Keep it short')).toBeInTheDocument();
    expect(box).toHaveValue('');
  });

  it('shows a duplicate only once', async () => {
    serve([{ id: 'a', text: 'Answer in Dutch' }]);
    const { user, box } = renderSection();
    await screen.findByText('Answer in Dutch');

    await user.type(box, 'answer in dutch{Enter}');

    await expect.poll(() => box).toHaveValue('');
    expect(screen.getAllByRole('listitem')).toHaveLength(1);
  });

  it('only enables Add once there is text', async () => {
    serve([]);
    const { user, box, addButton } = renderSection();
    expect(addButton).toBeDisabled();

    await user.type(box, '   ');
    expect(addButton).toBeDisabled();

    await user.type(box, 'x');
    expect(addButton).toBeEnabled();
  });

  it('says to remove one when the user is at the cap, keeping what they typed', async () => {
    serve([], { full: true });
    const { user, box } = renderSection();

    await user.type(box, 'One too many{Enter}');

    expect(await screen.findByText(/remove one first/)).toBeInTheDocument();
    expect(box).toHaveValue('One too many');
  });

  it('removes a preference, even one already gone on the server', async () => {
    const saved = [
      { id: 'a', text: 'Answer in Dutch' },
      { id: 'b', text: 'Keep it short' },
    ];
    serve(saved);
    const { user } = renderSection();
    await screen.findByText('Answer in Dutch');
    saved.splice(1, 1); // forgotten in a chat since the page loaded

    await user.click(screen.getByRole('button', { name: 'Remove "Answer in Dutch"' }));
    await user.click(screen.getByRole('button', { name: 'Remove "Keep it short"' }));

    expect(await screen.findByText('No preferences yet.')).toBeInTheDocument();
    expect(screen.queryByText(/Couldn't remove/)).not.toBeInTheDocument();
  });
});
