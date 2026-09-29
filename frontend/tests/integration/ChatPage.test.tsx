import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { ConversationsProvider } from '../../src/context/ConversationsProvider';
import { ChatPage } from '../../src/pages/ChatPage';
import type { Schemas } from '../../src/types';
import { server, sse } from '../server';

// The real page, hook and API client; only the backend is faked (see ../server.ts).
function renderChat(path: string) {
  const router = createMemoryRouter(
    [
      {
        path: '/chat/:conversationId?',
        element: (
          <ConversationsProvider>
            <ChatPage />
          </ConversationsProvider>
        ),
      },
    ],
    { initialEntries: [path] },
  );
  render(<RouterProvider router={router} />);
  return { router, user: userEvent.setup() };
}

const newConversation: Schemas['ConversationResponse'] = {
  id: '6b1c4f0e-2d3a-4c5b-9e8f-7a6b5c4d3e2f',
  title: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

async function ask(user: ReturnType<typeof userEvent.setup>, question: string) {
  await user.type(screen.getByPlaceholderText('Type a message...'), `${question}{Enter}`);
}

describe('ChatPage', () => {
  it('streams an answer with its sources into a new chat', async () => {
    let sent: Schemas['MessageRequest'] | undefined;
    server.use(
      http.post('/api/conversations', () =>
        HttpResponse.json(newConversation),
      ),
      http.post('/api/conversations/:id/messages', async ({ params, request }) => {
        expect(params.id).toBe(newConversation.id);
        sent = (await request.json()) as Schemas['MessageRequest'];
        return sse([
          ['tool_start', { name: 'search_kb', query: 'plans' }],
          ['tool_result', { name: 'search_kb', output: '2 chunks' }],
          ['text', { text: 'We offer ' }],
          ['text', { text: 'three plans.' }],
          ['sources', { sources: ['02-plans-and-pricing.md'] }],
        ]);
      }),
    );
    const { router, user } = renderChat('/chat');

    await ask(user, 'What plans are there?');

    expect(await screen.findByText('We offer three plans.')).toBeInTheDocument();
    expect(screen.getByText('What plans are there?')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /search_kb/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '02-plans-and-pricing.md' })).toBeInTheDocument();
    expect(screen.queryByLabelText('Assistant is typing')).not.toBeInTheDocument();

    // The new chat was created first, and the URL follows it.
    expect(router.state.location.pathname).toBe(`/chat/${newConversation.id}`);
    expect(sent?.message).toBe('What plans are there?');
  });

  it('shows an error bubble when the stream fails to open', async () => {
    server.use(
      http.post('/api/conversations', () =>
        HttpResponse.json(newConversation),
      ),
      http.post('/api/conversations/:id/messages', () => new HttpResponse(null, { status: 500 })),
    );
    const { user } = renderChat('/chat');

    await ask(user, 'hello');

    expect(await screen.findByText(/Something went wrong/)).toBeInTheDocument();
  });

  it('loads a saved conversation from its URL', async () => {
    server.use(
      http.get('/api/conversations/:id/messages', () =>
        HttpResponse.json<Schemas['HistoryMessageResponse'][]>([
          { role: 'user', text: 'How long is data kept?', sources: null },
          { role: 'assistant', text: 'Ninety days.', sources: ['11-data-retention-policy.md'] },
        ]),
      ),
    );
    renderChat('/chat/c1');

    expect(await screen.findByText('Ninety days.')).toBeInTheDocument();
    expect(screen.getByText('How long is data kept?')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '11-data-retention-policy.md' })).toBeInTheDocument();
  });

  it('says none were found only for answers that searched', async () => {
    server.use(
      http.get('/api/conversations/:id/messages', () =>
        HttpResponse.json<Schemas['HistoryMessageResponse'][]>([
          { role: 'user', text: 'hi', sources: null },
          { role: 'assistant', text: 'Hello!', sources: null },
          { role: 'user', text: 'Who won the cup?', sources: null },
          { role: 'assistant', text: "I don't know.", sources: [] },
        ]),
      ),
    );
    renderChat('/chat/c1');

    expect(await screen.findByText("I don't know.")).toBeInTheDocument();
    expect(screen.getAllByText('— none found')).toHaveLength(1);
  });

  it('explains when the conversation in the URL does not exist', async () => {
    server.use(
      http.get('/api/conversations/:id/messages', () => new HttpResponse(null, { status: 404 })),
    );
    renderChat('/chat/missing');

    expect(
      await screen.findByText("This conversation doesn't exist or was deleted."),
    ).toBeInTheDocument();
  });
});
