import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { ApiError, api, setAccessToken, unwrap } from '@/shared/api/client';
import { errorDetail, errorMessage, errorStatus, ignoreNotFound } from '@/shared/api/errors';
import type { PreferenceRequest } from '@/shared/types';
import { server } from '../../server';

const URL = '/api/settings/preferences';

describe('the typed api client', () => {
  it('refreshes an expired session and resends the request, body included', async () => {
    const seen: { auth: string | null; body: PreferenceRequest }[] = [];
    server.use(
      http.post(URL, async ({ request }) => {
        seen.push({ auth: request.headers.get('Authorization'), body: (await request.json()) as PreferenceRequest });
        return seen.length === 1
          ? new HttpResponse(null, { status: 401 })
          : HttpResponse.json({ id: 'p1', text: 'Be brief' });
      }),
      http.post('/api/auth/refresh', () => HttpResponse.json({ access_token: 'new', token_type: 'bearer' })),
    );
    setAccessToken('old');

    const saved = await unwrap(api.POST(URL, { body: { text: 'Be brief' } }));

    expect(saved).toEqual({ id: 'p1', text: 'Be brief' });
    expect(seen).toEqual([
      { auth: 'Bearer old', body: { text: 'Be brief' } },
      { auth: 'Bearer new', body: { text: 'Be brief' } },
    ]);
  });

  it("throws an ApiError carrying the backend's reason", async () => {
    server.use(http.post(URL, () => HttpResponse.json({ detail: 'Too many preferences' }, { status: 409 })));

    const err = await unwrap(api.POST(URL, { body: { text: 'x' } })).catch((e: unknown) => e);

    expect(err).toBeInstanceOf(ApiError);
    expect(errorStatus(err)).toBe(409);
    expect(errorDetail(err)).toBe('Too many preferences');
  });

  it('has no reason to give for an error page that is not JSON', async () => {
    server.use(http.post(URL, () => new HttpResponse('<html>413</html>', { status: 413 })));

    const err = await unwrap(api.POST(URL, { body: { text: 'x' } })).catch((e: unknown) => e);

    expect(errorStatus(err)).toBe(413);
    expect(errorDetail(err)).toBeNull();
  });
});

describe('errorMessage', () => {
  it("picks the message for the error's status, else the fallback", () => {
    expect(errorMessage(new ApiError(404, 'x'), { 404: 'Gone' }, 'Failed')).toBe('Gone');
    expect(errorMessage(new ApiError(500, 'x'), { 404: 'Gone' }, 'Failed')).toBe('Failed');
    expect(errorMessage(new TypeError('Failed to fetch'), { 404: 'Gone' }, 'Failed')).toBe('Failed');
  });
});

describe('ignoreNotFound', () => {
  it('treats a 404 as done, and passes any other failure on', async () => {
    await expect(ignoreNotFound(Promise.reject(new ApiError(404, 'x')))).resolves.toBeUndefined();
    await expect(ignoreNotFound(Promise.reject(new ApiError(500, 'x')))).rejects.toThrow();
  });
});
