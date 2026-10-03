import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { Sidebar } from '@/app/layout/Sidebar';
import { AuthContext } from '@/features/auth/hooks/useAuth';
import type { ConversationPageResponse } from '@/shared/types';
import { withQueryClient } from '../queryClient';
import { server } from '../server';

const page: ConversationPageResponse = {
  items: [
    {
      id: '6b1c4f0e-2d3a-4c5b-9e8f-7a6b5c4d3e2f',
      title: 'Plans and pricing',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
  ],
  next_cursor: null,
};

// The real sidebar, hooks and API client; only the backend is faked (see ../server.ts).
function renderSidebar() {
  server.use(http.get('/api/conversations', () => HttpResponse.json(page)));
  const router = createMemoryRouter(
    [
      {
        path: '*',
        element: (
          <AuthContext
            value={{
              status: 'authenticated',
              user: { id: 'u1', email: 'a@example.com', is_admin: false },
              login: async () => {},
              logout: async () => {},
            }}
          >
            <Sidebar />
          </AuthContext>
        ),
      },
    ],
    { initialEntries: ['/chat'] },
  );
  render(withQueryClient(<RouterProvider router={router} />));
  return userEvent.setup();
}

async function openDeleteDialog(user: ReturnType<typeof userEvent.setup>) {
  await screen.findByRole('link', { name: 'Plans and pricing' });
  await user.click(screen.getByTitle('Delete chat'));
  return screen.getByRole('dialog', { name: 'Delete chat?' });
}

describe('Sidebar delete chat', () => {
  it('keeps the chat when the user cancels', async () => {
    const user = renderSidebar();

    const dialog = await openDeleteDialog(user);
    expect(dialog).toHaveTextContent('“Plans and pricing” will be permanently deleted.');
    expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus();

    await user.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Plans and pricing' })).toBeInTheDocument();
  });

  it('closes on Escape', async () => {
    const user = renderSidebar();

    await openDeleteDialog(user);
    await user.keyboard('{Escape}');

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('deletes the chat once confirmed', async () => {
    server.use(http.delete('/api/conversations/:id', () => new HttpResponse(null, { status: 204 })));
    const user = renderSidebar();

    await openDeleteDialog(user);
    await user.click(screen.getByRole('button', { name: 'Delete' }));

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(screen.queryByRole('link', { name: 'Plans and pricing' })).not.toBeInTheDocument();
  });

  it('shows a failed delete in the dialog so the user can retry', async () => {
    server.use(http.delete('/api/conversations/:id', () => new HttpResponse(null, { status: 500 })));
    const user = renderSidebar();

    await openDeleteDialog(user);
    await user.click(screen.getByRole('button', { name: 'Delete' }));

    expect(await screen.findByRole('alert')).toHaveTextContent("Couldn't delete the chat.");
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Plans and pricing' })).toBeInTheDocument();
  });
});
