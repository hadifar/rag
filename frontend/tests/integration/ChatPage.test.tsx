import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { uploadAttachment } from '@/features/chat/api/attachments';
import { ChatPage } from '@/pages/ChatPage';
import type {
  AttachmentResponse,
  ChatMessageRequest,
  ConversationResponse,
  ConversationUpdateRequest,
  HistoryMessageResponse,
  MessageRequest,
} from '@/shared/types';
import { withQueryClient } from '../queryClient';
import { server, sse } from '../server';

// jsdom's FormData can't carry a File into a fetch Request here (the browser's can), so
// the upload is the one call faked above the network.
vi.mock('@/features/chat/api/attachments', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/features/chat/api/attachments')>()),
  uploadAttachment: vi.fn(),
}));

// The real page, hook and API client; only the backend is faked (see ../server.ts).
function renderChat(path: string) {
  const router = createMemoryRouter(
    [
      {
        path: '/chat/:conversationId?',
        element: <ChatPage />,
      },
    ],
    { initialEntries: [path] },
  );
  render(withQueryClient(<RouterProvider router={router} />));
  return { router, user: userEvent.setup() };
}

const newConversation: ConversationResponse = {
  id: '6b1c4f0e-2d3a-4c5b-9e8f-7a6b5c4d3e2f',
  title: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  pinned_at: null,
  model: 'gpt-6-luna',
  effort: 'low',
};

async function ask(user: ReturnType<typeof userEvent.setup>, question: string) {
  await user.type(screen.getByPlaceholderText('Type a message...'), `${question}{Enter}`);
}

describe('ChatPage', () => {
  it('streams an answer with its sources into a new chat', async () => {
    let sent: MessageRequest | undefined;
    server.use(
      http.post('/api/conversations', () =>
        HttpResponse.json(newConversation),
      ),
      http.post('/api/chat/:id', async ({ params, request }) => {
        expect(params.id).toBe(newConversation.id);
        sent = (await request.json()) as MessageRequest;
        return sse([
          { type: 'tool', name: 'search_kb', status: 'pending', query: 'plans' },
          { type: 'tool', name: 'search_kb', status: 'done', output: '2 chunks' },
          { type: 'text', text: 'We offer ' },
          { type: 'text', text: 'three plans.' },
          { type: 'artifacts', artifacts: [{ kind: 'source', id: '02-plans-and-pricing.md' }] },
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
      http.post('/api/chat/:id', () => new HttpResponse(null, { status: 500 })),
    );
    const { user } = renderChat('/chat');

    await ask(user, 'hello');

    expect(await screen.findByText(/Something went wrong/)).toBeInTheDocument();
  });

  it('loads a saved conversation from its URL, reasoning and plan included', async () => {
    server.use(
      http.get('/api/conversations/:id/messages', () =>
        HttpResponse.json<HistoryMessageResponse[]>([
          { role: 'user', text: 'How long is data kept?', attachments: [] },
          {
            role: 'assistant',
            events: [
              { type: 'reasoning', text: 'Check the retention policy.' },
              { type: 'todos', todos: [{ content: 'Find the policy', status: 'completed' }] },
              { type: 'tool', name: 'search_kb', status: 'pending', query: 'retention' },
              { type: 'tool', name: 'search_kb', status: 'done', output: '1 chunk' },
              { type: 'text', text: 'Ninety days.' },
              { type: 'artifacts', artifacts: [{ kind: 'source', id: '11-data-retention-policy.md' }] },
            ],
          },
        ]),
      ),
    );
    const { user } = renderChat('/chat/c1');

    expect(await screen.findByText('Ninety days.')).toBeInTheDocument();
    expect(screen.getByText('How long is data kept?')).toBeInTheDocument();
    // Finished, as it was once the answer began, and folded until opened.
    const thoughts = screen.getByRole('button', { name: 'Thought process' });
    expect(thoughts).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText('Check the retention policy.')).not.toBeInTheDocument();
    await user.click(thoughts);
    expect(screen.getByText('Check the retention policy.')).toBeInTheDocument();
    expect(screen.getByText('Find the policy')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '11-data-retention-policy.md' })).toBeInTheDocument();
  });

  it('says none were found only for answers that searched', async () => {
    server.use(
      http.get('/api/conversations/:id/messages', () =>
        HttpResponse.json<HistoryMessageResponse[]>([
          { role: 'user', text: 'hi', attachments: [] },
          { role: 'assistant', events: [{ type: 'text', text: 'Hello!' }] },
          { role: 'user', text: 'Who won the cup?', attachments: [] },
          {
            role: 'assistant',
            events: [
              { type: 'text', text: "I don't know." },
              { type: 'artifacts', artifacts: [] },
            ],
          },
        ]),
      ),
    );
    renderChat('/chat/c1');

    expect(await screen.findByText("I don't know.")).toBeInTheDocument();
    expect(screen.getAllByText('— none found')).toHaveLength(1);
  });

  it('adds a follow-up to a saved conversation below its history', async () => {
    server.use(
      http.get('/api/conversations/:id/messages', () =>
        HttpResponse.json<HistoryMessageResponse[]>([
          { role: 'user', text: 'hi', attachments: [] },
          { role: 'assistant', events: [{ type: 'text', text: 'Hello!' }] },
        ]),
      ),
      http.post('/api/chat/:id', () => sse([{ type: 'text', text: 'Sure.' }])),
    );
    const { user } = renderChat('/chat/c1');
    await screen.findByText('Hello!');

    await ask(user, 'One more thing');

    expect(await screen.findByText('Sure.')).toBeInTheDocument();
    expect(screen.getByText('Hello!')).toBeInTheDocument();
    expect(screen.getByText('One more thing')).toBeInTheDocument();
  });

  it('starts the next new chat empty', async () => {
    server.use(
      http.post('/api/conversations', () => HttpResponse.json(newConversation)),
      http.post('/api/chat/:id', () => sse([{ type: 'text', text: 'Hi there.' }])),
      http.post('/api/conversations/:id/title', () => HttpResponse.json(newConversation)),
    );
    const { router, user } = renderChat('/chat');
    await ask(user, 'hello');
    await screen.findByText('Hi there.');

    await act(() => router.navigate('/chat'));

    expect(screen.getByText(/ask me something/)).toBeInTheDocument();
    expect(screen.queryByText('hello')).not.toBeInTheDocument();
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

  it('sends a file without text to a new chat, named after the file', async () => {
    const notes: AttachmentResponse = { id: 'a1', name: 'notes.md', media_type: 'text/markdown', size: 7 };
    vi.mocked(uploadAttachment).mockResolvedValueOnce(notes);
    let sent: ChatMessageRequest | undefined;
    let titledFrom: string | undefined;
    server.use(
      http.post('/api/conversations', () => HttpResponse.json(newConversation)),
      http.post('/api/chat/:id', async ({ request }) => {
        sent = (await request.json()) as ChatMessageRequest;
        return sse([{ type: 'text', text: 'These are setup notes.' }]);
      }),
      http.post('/api/conversations/:id/title', async ({ request }) => {
        titledFrom = ((await request.json()) as MessageRequest).message;
        return HttpResponse.json({ ...newConversation, title: 'Setup notes' });
      }),
    );
    const { user } = renderChat('/chat');

    const file = new File(['# Notes'], 'notes.md');
    await user.upload(screen.getByTestId('attachment-input'), file);
    await vi.waitFor(() => expect(screen.getByRole('button', { name: 'Send' })).toBeEnabled());
    await user.click(screen.getByRole('button', { name: 'Send' }));

    expect(await screen.findByText('These are setup notes.')).toBeInTheDocument();
    // Uploaded to the new chat, before it had a URL.
    expect(uploadAttachment).toHaveBeenCalledExactlyOnceWith(newConversation.id, file);
    expect(sent).toEqual({ message: '', attachment_ids: ['a1'] });
    expect(titledFrom).toBe('notes.md');
    // Sent: the composer is empty again, and the message shows the file.
    expect(screen.queryByRole('button', { name: 'Remove notes.md' })).not.toBeInTheDocument();
    expect(screen.getByRole('log')).toHaveTextContent('notes.md');
  });

  it("sends a new chat's message to the conversation its files went to", async () => {
    const notes: AttachmentResponse = { id: 'a1', name: 'notes.md', media_type: 'text/markdown', size: 7 };
    vi.mocked(uploadAttachment).mockResolvedValueOnce(notes);
    // Another tab sends to the user's empty conversation after the upload: asking again
    // would now give a different one, without the file.
    const later: ConversationResponse = { ...newConversation, id: '0f9e8d7c-6b5a-4c3d-8e2f-1a0b9c8d7e6f' };
    let creates = 0;
    let sentTo: string | undefined;
    server.use(
      http.post('/api/conversations', () => HttpResponse.json(creates++ === 0 ? newConversation : later)),
      http.post('/api/chat/:id', ({ params }) => {
        sentTo = params.id as string;
        return sse([{ type: 'text', text: 'These are setup notes.' }]);
      }),
      http.post('/api/conversations/:id/title', () =>
        HttpResponse.json({ ...newConversation, title: 'Setup notes' }),
      ),
    );
    const { router, user } = renderChat('/chat');

    await user.upload(screen.getByTestId('attachment-input'), new File(['# Notes'], 'notes.md'));
    await vi.waitFor(() => expect(screen.getByRole('button', { name: 'Send' })).toBeEnabled());
    await ask(user, 'Summarize these');

    expect(await screen.findByText('These are setup notes.')).toBeInTheDocument();
    expect(sentTo).toBe(newConversation.id);
    expect(creates).toBe(1);
    expect(router.state.location.pathname).toBe(`/chat/${newConversation.id}`);
  });

  it('discards a file removed before sending', async () => {
    const notes: AttachmentResponse = { id: 'a1', name: 'notes.md', media_type: 'text/markdown', size: 7 };
    vi.mocked(uploadAttachment).mockResolvedValueOnce(notes);
    let discarded: string | undefined;
    server.use(
      http.get('/api/conversations/:id/messages', () => HttpResponse.json([])),
      http.delete('/api/conversations/:id/attachments/:attachmentId', ({ params }) => {
        discarded = params.attachmentId as string;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user } = renderChat('/chat/c1');

    await user.upload(screen.getByTestId('attachment-input'), new File(['# Notes'], 'notes.md'));
    await vi.waitFor(() => expect(screen.queryByText('Uploading…')).not.toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: 'Remove notes.md' }));

    await vi.waitFor(() => expect(discarded).toBe('a1'));
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled();
  });

  it("shows the conversation's model and effort, and saves a new pick", async () => {
    let saved: ConversationUpdateRequest | undefined;
    server.use(
      http.get('/api/conversations/:id/messages', () => HttpResponse.json([])),
      http.get('/api/conversations/:id', () =>
        HttpResponse.json<ConversationResponse>({ ...newConversation, model: 'gpt-6-astra', effort: 'medium' }),
      ),
      http.patch('/api/conversations/:id', async ({ request }) => {
        saved = (await request.json()) as ConversationUpdateRequest;
        return HttpResponse.json<ConversationResponse>({ ...newConversation, model: 'gpt-6-astra', effort: 'max' });
      }),
    );
    const { user } = renderChat(`/chat/${newConversation.id}`);

    expect(await screen.findByRole('button', { name: 'Model: gpt-6-astra' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Effort: Medium' }));
    await user.click(screen.getByRole('menuitemradio', { name: 'Max' }));

    expect(await screen.findByRole('button', { name: 'Effort: Max' })).toBeInTheDocument();
    expect(saved).toEqual({ effort: 'max' });
  });

  it("sets a new chat to the model picked before its first message goes", async () => {
    const calls: string[] = [];
    server.use(
      http.post('/api/conversations', () => HttpResponse.json(newConversation)),
      http.patch('/api/conversations/:id', async ({ request }) => {
        calls.push(`patch ${JSON.stringify(await request.json())}`);
        return HttpResponse.json<ConversationResponse>({ ...newConversation, model: 'gpt-6-sol' });
      }),
      http.post('/api/chat/:id', () => {
        calls.push('chat');
        return sse([{ type: 'text', text: 'Hi.' }]);
      }),
      http.post('/api/conversations/:id/title', () => HttpResponse.json(newConversation)),
      // Once the URL has its id, the page reads the conversation as the server keeps it.
      http.get('/api/conversations/:id', () =>
        HttpResponse.json<ConversationResponse>({ ...newConversation, model: 'gpt-6-sol' }),
      ),
    );
    const { user } = renderChat('/chat');

    await user.click(screen.getByRole('button', { name: 'Model: gpt-6-luna' }));
    await user.click(screen.getByRole('menuitemradio', { name: 'gpt-6-sol' }));
    await ask(user, 'hello');

    expect(await screen.findByText('Hi.')).toBeInTheDocument();
    expect(calls).toEqual(['patch {"model":"gpt-6-sol"}', 'chat']);
    expect(screen.getByRole('button', { name: 'Model: gpt-6-sol' })).toBeInTheDocument();
  });
});
