import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { Sidebar } from '@/app/layout/Sidebar';
import { AuthContext } from '@/features/auth/hooks/useAuth';
import type { ConversationPageResponse, ConversationResponse } from '@/shared/types';
import { withQueryClient } from '../queryClient';
import { server } from '../server';

const page: ConversationPageResponse = {
  items: [
    {
      id: '6b1c4f0e-2d3a-4c5b-9e8f-7a6b5c4d3e2f',
      title: 'Plans and pricing',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      pinned_at: null,
      model: 'gpt-6-luna',
      effort: 'low',
    },
  ],
  next_cursor: null,
};

// The real sidebar, hooks and API client; only the backend is faked (see ../server.ts).
function renderSidebar(pinned: ConversationResponse[] = []) {
  server.use(
    http.get('/api/conversations', () => HttpResponse.json(page)),
    http.get('/api/conversations/pinned', () => HttpResponse.json(pinned)),
  );
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

type User = ReturnType<typeof userEvent.setup>;

async function chooseFromMenu(user: User, item: string, chat = 'Plans and pricing') {
  const link = await screen.findByRole('link', { name: chat });
  const row = link.parentElement!;
  await user.click(within(row).getByRole('button', { name: 'Chat options' }));
  await user.click(screen.getByRole('menuitem', { name: item }));
}

async function openDeleteDialog(user: User) {
  await chooseFromMenu(user, 'Delete');
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

  it('vaporizes the chat once confirmed, then removes it', async () => {
    server.use(http.delete('/api/conversations/:id', () => new HttpResponse(null, { status: 204 })));
    const user = renderSidebar();

    await openDeleteDialog(user);
    await user.click(screen.getByRole('button', { name: 'Delete' }));

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    // Gone for assistive tech at once; still on screen while its exit plays.
    expect(screen.queryByRole('link', { name: 'Plans and pricing' })).not.toBeInTheDocument();
    const row = screen.getByText('Plans and pricing').parentElement!;
    expect(row).toHaveClass('animate-vaporize');

    fireEvent.animationEnd(row);

    await waitFor(() => expect(screen.queryByText('Plans and pricing')).not.toBeInTheDocument());
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

const chat = page.items[0]!;

describe('Sidebar chat menu', () => {
  it('opens from the dots, focuses its first item and closes on Escape', async () => {
    const user = renderSidebar();
    await screen.findByRole('link', { name: 'Plans and pricing' });
    const dots = screen.getByRole('button', { name: 'Chat options' });

    await user.click(dots);

    expect(screen.getByRole('menuitem', { name: 'Pin' })).toHaveFocus();
    await user.keyboard('{ArrowDown}');
    expect(screen.getByRole('menuitem', { name: 'Rename' })).toHaveFocus();
    await user.keyboard('{ArrowUp}{ArrowUp}');
    expect(screen.getByRole('menuitem', { name: 'Delete' })).toHaveFocus();

    await user.keyboard('{Escape}');

    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    expect(dots).toHaveFocus();
  });

  it('pins a chat into the Pinned section', async () => {
    server.use(
      http.patch('/api/conversations/:id', () =>
        HttpResponse.json({ ...chat, pinned_at: '2026-01-02T00:00:00Z' }),
      ),
    );
    const user = renderSidebar();

    await chooseFromMenu(user, 'Pin');

    const pinnedLabel = await screen.findByText('Pinned');
    expect(pinnedLabel.parentElement).toHaveTextContent('Plans and pricing');
    expect(screen.queryByText('Recent')).not.toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: 'Plans and pricing' })).toHaveLength(1);
  });

  it('unpins a chat back into the recent ones', async () => {
    const pinned = { ...chat, id: 'pinned-1', title: 'Refunds', pinned_at: '2026-01-02T00:00:00Z' };
    server.use(
      http.patch('/api/conversations/:id', () => HttpResponse.json({ ...pinned, pinned_at: null })),
    );
    const user = renderSidebar([pinned]);

    await chooseFromMenu(user, 'Unpin', 'Refunds');

    await waitFor(() => expect(screen.queryByText('Pinned')).not.toBeInTheDocument());
    expect(screen.getByRole('link', { name: 'Refunds' })).toBeInTheDocument();
  });

  it('renames a chat in place on Enter', async () => {
    let sent: unknown;
    server.use(
      http.patch('/api/conversations/:id', async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json({ ...chat, title: 'Billing' });
      }),
    );
    const user = renderSidebar();

    await chooseFromMenu(user, 'Rename');
    const field = screen.getByRole('textbox', { name: 'Chat title' });
    expect(field).toHaveFocus();
    await user.clear(field);
    await user.type(field, '  Billing  {Enter}');

    expect(await screen.findByRole('link', { name: 'Billing' })).toBeInTheDocument();
    expect(sent).toEqual({ title: 'Billing' });
  });

  it('keeps the title when the rename is cancelled with Escape', async () => {
    const user = renderSidebar();

    await chooseFromMenu(user, 'Rename');
    await user.type(screen.getByRole('textbox', { name: 'Chat title' }), 'x{Escape}');

    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Plans and pricing' })).toBeInTheDocument();
  });

  it('keeps the field open with the error when the rename fails', async () => {
    server.use(http.patch('/api/conversations/:id', () => new HttpResponse(null, { status: 500 })));
    const user = renderSidebar();

    await chooseFromMenu(user, 'Rename');
    await user.type(screen.getByRole('textbox', { name: 'Chat title' }), ' v2{Enter}');

    expect(await screen.findByRole('alert')).toHaveTextContent("Couldn't rename the chat.");
    expect(screen.getByRole('textbox', { name: 'Chat title' })).toHaveValue('Plans and pricing v2');
  });
});

describe('Sidebar share chat', () => {
  const shareUrl = `/api/conversations/${chat.id}/share`;
  const share = { id: 'share-1', title: chat.title!, shared_at: '2026-03-04T10:00:00Z' };

  it('creates a link, copies it, and stops sharing', async () => {
    let current: typeof share | null = null;
    server.use(
      http.get(shareUrl, () => HttpResponse.json(current)),
      http.put(shareUrl, () => HttpResponse.json((current = share))),
      http.delete(shareUrl, () => {
        current = null;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const user = renderSidebar();

    await chooseFromMenu(user, 'Share');
    const dialog = screen.getByRole('dialog', { name: 'Share chat' });
    await user.click(await within(dialog).findByRole('button', { name: 'Create link' }));

    const link = await within(dialog).findByRole('textbox', { name: 'Share link' });
    expect(link).toHaveValue(`${window.location.origin}/share/share-1`);
    await user.click(within(dialog).getByRole('button', { name: 'Copy' }));
    expect(await navigator.clipboard.readText()).toBe(`${window.location.origin}/share/share-1`);
    expect(within(dialog).getByRole('button', { name: 'Copied' })).toBeInTheDocument();

    await user.click(within(dialog).getByRole('button', { name: 'Stop sharing' }));
    expect(await within(dialog).findByRole('button', { name: 'Create link' })).toBeInTheDocument();
  });

  it('shows why sharing failed', async () => {
    server.use(
      http.get(shareUrl, () => HttpResponse.json(null)),
      http.put(shareUrl, () => HttpResponse.json({ detail: 'empty' }, { status: 409 })),
    );
    const user = renderSidebar();

    await chooseFromMenu(user, 'Share');
    await user.click(await screen.findByRole('button', { name: 'Create link' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('no messages to share yet');
  });
});
