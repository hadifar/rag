import { render, screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { SharedChatPage } from '@/pages/SharedChatPage';
import type { SharedConversationResponse } from '@/shared/types';
import { withQueryClient } from '../queryClient';
import { server } from '../server';

const SHARE_ID = '0f6c1b2a-3d4e-4f5a-8b9c-0d1e2f3a4b5c';

const shared: SharedConversationResponse = {
  title: 'Plans and pricing',
  shared_at: '2026-03-04T10:00:00Z',
  messages: [
    { role: 'user', text: 'What plans are there?' },
    {
      role: 'assistant',
      events: [
        { type: 'text', text: 'There are three plans.' },
        { type: 'artifacts', artifacts: [{ kind: 'source', id: 'pricing.md' }] },
      ],
    },
  ],
};

// The real page, hook and API client; only the backend is faked (see ../server.ts).
function renderShared() {
  const router = createMemoryRouter([{ path: '/share/:shareId', element: <SharedChatPage /> }], {
    initialEntries: [`/share/${SHARE_ID}`],
  });
  render(withQueryClient(<RouterProvider router={router} />));
}

describe('SharedChatPage', () => {
  it('shows the snapshot read-only, without a session', async () => {
    let authorization: string | null = 'unset';
    server.use(
      http.get(`/api/shares/${SHARE_ID}`, ({ request }) => {
        authorization = request.headers.get('Authorization');
        return HttpResponse.json(shared);
      }),
    );
    renderShared();

    expect(await screen.findByRole('heading', { name: 'Plans and pricing' })).toBeInTheDocument();
    expect(screen.getByText(/^Shared on .* · read-only$/)).toBeInTheDocument();
    expect(screen.getByText('What plans are there?')).toBeInTheDocument();
    expect(screen.getByText('There are three plans.')).toBeInTheDocument();
    // A signed-out reader can't open documents: the source is a plain name, not a button.
    expect(screen.getByText('pricing.md')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'pricing.md' })).not.toBeInTheDocument();
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    expect(authorization).toBeNull();
  });

  it('says so when the link was taken down', async () => {
    server.use(
      http.get(`/api/shares/${SHARE_ID}`, () =>
        HttpResponse.json({ detail: 'gone' }, { status: 404 }),
      ),
    );
    renderShared();

    expect(await screen.findByRole('alert')).toHaveTextContent('This link was taken down');
  });
});
