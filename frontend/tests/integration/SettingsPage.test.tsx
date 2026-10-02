import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AuthContext } from '@/features/auth/hooks/useAuth';
import { SettingsPage } from '@/pages/SettingsPage';
import type { IngestionRunResponse, SettingsResponse } from '@/shared/types';
import { server } from '../server';

const running: IngestionRunResponse = {
  id: 'run-1',
  status: 'running',
  started_at: '2026-09-28T10:00:00Z',
  finished_at: null,
  added: null,
  updated: null,
  unchanged: null,
  removed: null,
  error: null,
};

const succeeded: IngestionRunResponse = {
  ...running,
  status: 'succeeded',
  finished_at: '2026-09-28T10:00:05Z',
  added: 2,
  updated: 0,
  unchanged: 0,
  removed: 0,
};

afterEach(() => vi.restoreAllMocks());

/**
 * Answers the upload POST itself; every other request still goes to MSW. vitest 5's
 * jsdom shim can't turn a jsdom File inside FormData into a Node request (it reads
 * Blob internals that jsdom 30 renamed), so an upload never reaches MSW. Real browsers
 * are unaffected. Returns the form data each upload sent.
 */
function answerUploads(respond: () => Response): FormData[] {
  const sent: FormData[] = [];
  const realFetch = globalThis.fetch;
  vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
    if (init?.method === 'POST' && init.body instanceof FormData) {
      sent.push(init.body);
      return Promise.resolve(respond());
    }
    return realFetch(input, init);
  });
  return sent;
}

// The real page, hooks and API client; only the backend is faked (see ../server.ts).
function renderSettings({ isAdmin = true, latest = null as IngestionRunResponse | null } = {}) {
  server.use(
    http.get('/api/settings', () =>
      HttpResponse.json<SettingsResponse>({ model: 'm', temperature: 0.2, top_k: 4 }),
    ),
    http.get('/api/ingestions/latest', () => HttpResponse.json(latest)),
  );
  render(
    <AuthContext
      value={{
        status: 'authenticated',
        user: { id: 'u1', email: 'a@example.com', is_admin: isAdmin },
        login: async () => {},
        logout: async () => {},
      }}
    >
      <SettingsPage />
    </AuthContext>,
  );
  return userEvent.setup();
}

async function uploadZip(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole('button', { name: 'Upload knowledge base' }));
  const zip = new File(['PK'], 'kb.zip', { type: 'application/zip' });
  await user.upload(screen.getByLabelText('Knowledge base zip'), zip);
  await user.click(screen.getByRole('button', { name: 'Upload' }));
}

describe('SettingsPage knowledge base', () => {
  it('is hidden from users who are not admins', async () => {
    renderSettings({ isAdmin: false });

    expect(await screen.findByText('Settings')).toBeInTheDocument();
    expect(screen.queryByText('Knowledge base')).not.toBeInTheDocument();
  });

  it('uploads a zip and waits for the ingestion to finish', async () => {
    let polls = 0;
    const sent = answerUploads(() => HttpResponse.json(running, { status: 202 }));
    server.use(
      http.get('/api/ingestions/run-1', () => {
        polls += 1;
        return HttpResponse.json(polls === 1 ? running : succeeded);
      }),
    );
    const user = renderSettings();

    await uploadZip(user);

    expect(await screen.findByRole('status')).toHaveTextContent('Indexing…');
    expect(sent).toHaveLength(1);
    const file = sent[0]?.get('file');
    expect(file).toBeInstanceOf(File);
    expect((file as File).name).toBe('kb.zip');
    // The second status check, one poll interval later, sees it finished.
    expect(
      await screen.findByText('Done: 2 added (2 documents)', {}, { timeout: 3000 }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Last upload/)).toHaveTextContent('2 added (2 documents)');
    // The file input came back empty, so the button can't resend the old file.
    expect(screen.getByRole('button', { name: 'Upload' })).toBeDisabled();
  });

  it("shows the backend's reason when an upload is rejected", async () => {
    answerUploads(() =>
      HttpResponse.json(
        { detail: 'Invalid knowledge-base archive: not a zip file' },
        { status: 400 },
      ),
    );
    const user = renderSettings();

    await uploadZip(user);

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Invalid knowledge-base archive: not a zip file',
    );

    // Escape closes the dialog even though focus left it with the upload button.
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('explains a file too large for the proxy', async () => {
    answerUploads(() => new HttpResponse('<html>413</html>', { status: 413 }));
    const user = renderSettings();

    await uploadZip(user);

    expect(await screen.findByRole('alert')).toHaveTextContent('larger than 20 MB');
  });

  it('picks a still running ingestion back up on load', async () => {
    server.use(http.get('/api/ingestions/run-1', () => HttpResponse.json(running)));
    const user = renderSettings({ latest: running });

    await user.click(await screen.findByRole('button', { name: 'Show upload progress' }));

    expect(screen.getByRole('status')).toHaveTextContent('Indexing…');
  });
});
