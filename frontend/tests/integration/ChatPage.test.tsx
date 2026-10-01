import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { ConversationsProvider } from '../../src/context/ConversationsProvider';
import { ChatPage } from '../../src/pages/ChatPage';
import type { ConversationResponse, HistoryMessageResponse, MessageRequest } from '../../src/types';
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

const newConversation: ConversationResponse = {
  id: '6b1c4f0e-2d3a-4c5b-9e8f-7a6b5c4d3e2f',
  title: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

async function ask(user: ReturnType<typeof userEvent.setup>, question: string) {
  await user.type(screen.getByPlaceholderText('Type a message...'), `${question}{Enter}`);
}

describe('ChatPage', () => {
  it('streams an answer with its references into a new chat', async () => {
    let sent: MessageRequest | undefined;
    server.use(
      http.post('/api/conversations', () =>
        HttpResponse.json(newConversation),
      ),
      http.post('/api/conversations/:id/messages', async ({ params, request }) => {
        expect(params.id).toBe(newConversation.id);
        sent = (await request.json()) as MessageRequest;
        return sse([
          { type: 'tool', name: 'search_kb', status: 'pending', query: 'plans' },
          { type: 'tool', name: 'search_kb', status: 'done', output: '2 chunks' },
          { type: 'text', text: 'We offer ' },
          { type: 'text', text: 'three plans.' },
          { type: 'references', references: ['02-plans-and-pricing.md'] },
        ]);
      }),
      http.post('/api/conversations/:id/title', () =>
        HttpResponse.json({ ...newConversation, title: 'Plans and pricing' }),
      ),
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

  it('loads a saved conversation from its URL, reasoning and plan included', async () => {
    server.use(
      http.get('/api/conversations/:id/messages', () =>
        HttpResponse.json<HistoryMessageResponse[]>([
          { role: 'user', text: 'How long is data kept?' },
          {
            role: 'assistant',
            events: [
              { type: 'reasoning', text: 'Check the retention policy.' },
              { type: 'todos', todos: [{ content: 'Find the policy', status: 'completed' }] },
              { type: 'tool', name: 'search_kb', status: 'pending', query: 'retention' },
              { type: 'tool', name: 'search_kb', status: 'done', output: '1 chunk' },
              { type: 'text', text: 'Ninety days.' },
              { type: 'references', references: ['11-data-retention-policy.md'] },
            ],
          },
        ]),
      ),
    );
    renderChat('/chat/c1');

    expect(await screen.findByText('Ninety days.')).toBeInTheDocument();
    expect(screen.getByText('How long is data kept?')).toBeInTheDocument();
    // Finished, as it was once the answer began.
    expect(screen.getByText('Thought process')).toBeInTheDocument();
    expect(screen.getByText('Check the retention policy.')).toBeInTheDocument();
    expect(screen.getByText('Find the policy')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '11-data-retention-policy.md' })).toBeInTheDocument();
  });

  it('says none were found only for answers that searched', async () => {
    server.use(
      http.get('/api/conversations/:id/messages', () =>
        HttpResponse.json<HistoryMessageResponse[]>([
          { role: 'user', text: 'hi' },
          { role: 'assistant', events: [{ type: 'text', text: 'Hello!' }] },
          { role: 'user', text: 'Who won the cup?' },
          {
            role: 'assistant',
            events: [
              { type: 'text', text: "I don't know." },
              { type: 'references', references: [] },
            ],
          },
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
