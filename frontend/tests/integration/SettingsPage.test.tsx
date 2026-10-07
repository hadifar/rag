import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AuthContext } from '@/features/auth/hooks/useAuth';
import { uploadKnowledgeBase } from '@/features/knowledge-base/api/ingestions';
import { uploadSkill } from '@/features/skills/api/skills';
import { SettingsPage } from '@/pages/SettingsPage';
import { ApiError } from '@/shared/api/client';
import type { IngestionRunResponse, SkillResponse } from '@/shared/types';
import { withQueryClient } from '../queryClient';
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

// jsdom's FormData can't carry a File into a fetch Request here (the browser's can), so
// the uploads are faked above the network.
vi.mock('@/features/skills/api/skills', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/features/skills/api/skills')>()),
  uploadSkill: vi.fn(),
}));
vi.mock('@/features/knowledge-base/api/ingestions', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/features/knowledge-base/api/ingestions')>()),
  uploadKnowledgeBase: vi.fn(),
}));

afterEach(() => vi.clearAllMocks());

// The real page, hooks and API client; only the backend is faked (see ../server.ts).
function renderSettings({ isAdmin = true, latest = null as IngestionRunResponse | null } = {}) {
  server.use(
    http.get('/api/ingestions/latest', () => HttpResponse.json(latest)),
  );
  render(
    withQueryClient(
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
    ),
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
    vi.mocked(uploadKnowledgeBase).mockResolvedValue(running);
    server.use(
      http.get('/api/ingestions/run-1', () => {
        polls += 1;
        return HttpResponse.json(polls === 1 ? running : succeeded);
      }),
    );
    const user = renderSettings();

    await uploadZip(user);

    expect(await screen.findByRole('status')).toHaveTextContent('Indexing…');
    expect(uploadKnowledgeBase).toHaveBeenCalledTimes(1);
    expect(vi.mocked(uploadKnowledgeBase).mock.calls[0]?.[0].name).toBe('kb.zip');
    // The second status check, one poll interval later, sees it finished.
    expect(
      await screen.findByText('Done: 2 added (2 documents)', {}, { timeout: 3000 }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Last upload/)).toHaveTextContent('2 added (2 documents)');
    // The file input came back empty, so the button can't resend the old file.
    expect(screen.getByRole('button', { name: 'Upload' })).toBeDisabled();
  });

  it("shows the backend's reason when an upload is rejected", async () => {
    vi.mocked(uploadKnowledgeBase).mockRejectedValue(
      new ApiError(400, 'Bad Request', 'Invalid knowledge-base archive: not a zip file'),
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
    // nginx's own HTML page: no `detail`.
    vi.mocked(uploadKnowledgeBase).mockRejectedValue(new ApiError(413, 'Payload Too Large'));
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

const notes: SkillResponse = {
  id: 's1',
  name: 'release-notes',
  description: 'Write release notes.',
  file_count: 0,
  created_at: '2026-10-07T10:00:00Z',
  updated_at: '2026-10-07T10:00:00Z',
};

describe('SettingsPage skills', () => {
  it('lists the user’s skills, or says there are none', async () => {
    renderSettings({ isAdmin: false });
    expect(await screen.findByText('No skills yet.')).toBeInTheDocument();
  });

  it('uploads a skill and adds it to the list', async () => {
    vi.mocked(uploadSkill).mockResolvedValue(notes);
    const user = renderSettings({ isAdmin: false });
    await screen.findByText('No skills yet.');

    const file = new File(['---'], 'SKILL.md', { type: 'text/markdown' });
    await user.upload(screen.getByLabelText('Skill file'), file);

    expect(await screen.findByText('release-notes')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Saved skill “release-notes”.');
    expect(uploadSkill).toHaveBeenCalledWith(file);
  });

  it('shows how many reference files a skill has', async () => {
    server.use(http.get('/api/skills', () => HttpResponse.json([{ ...notes, file_count: 2 }])));
    renderSettings({ isAdmin: false });

    expect(await screen.findByText('2 reference files')).toBeInTheDocument();
  });

  it('turns down a file over the size limit without uploading it', async () => {
    vi.mocked(uploadSkill).mockClear();
    const user = renderSettings({ isAdmin: false });
    await screen.findByText('No skills yet.');

    const big = new File(['x'.repeat(50 * 1024 + 1)], 'SKILL.md', { type: 'text/markdown' });
    await user.upload(screen.getByLabelText('Skill file'), big);

    expect(await screen.findByRole('status')).toHaveTextContent('larger than 50 KB');
    expect(uploadSkill).not.toHaveBeenCalled();
  });

  it("shows the backend's reason when a skill is rejected", async () => {
    vi.mocked(uploadSkill).mockRejectedValue(
      new ApiError(422, 'Unprocessable', 'Not a valid skill file: its frontmatter has no `name`'),
    );
    const user = renderSettings({ isAdmin: false });
    await screen.findByText('No skills yet.');

    await user.upload(screen.getByLabelText('Skill file'), new File(['x'], 'SKILL.md'));

    expect(await screen.findByRole('status')).toHaveTextContent('has no `name`');
  });

  it('deletes a skill once the user confirms', async () => {
    let deleted = false;
    server.use(
      http.get('/api/skills', () => HttpResponse.json(deleted ? [] : [notes])),
      http.delete('/api/skills/s1', () => {
        deleted = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const user = renderSettings({ isAdmin: false });

    await user.click(await screen.findByRole('button', { name: 'Delete release-notes' }));
    await user.click(screen.getByRole('button', { name: 'Delete' }));

    expect(await screen.findByText('No skills yet.')).toBeInTheDocument();
    expect(deleted).toBe(true);
  });
});
