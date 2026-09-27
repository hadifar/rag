// Absolute: a relative 'api' would resolve under nested routes like /chat/:id.
const API_BASE = '/api';

export function apiUrl(path: string): string {
  return `${API_BASE}/${path}`;
}

export function jsonPostInit(body: unknown) {
  return {
    method: 'POST' as const,
    headers: { 'Content-Type': 'application/json' } as Record<string, string>,
    body: JSON.stringify(body),
  };
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// The access token lives here, in memory only (never localStorage), so every api/*.ts
// module can send it and renew it without components passing it around.
let accessToken: string | null = null;
let pendingRefresh: Promise<boolean> | null = null;
const expiredListeners = new Set<() => void>();

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

/** Called when a request got a 401 and the refresh cookie couldn't renew the session. */
export function onSessionExpired(listener: () => void): () => void {
  expiredListeners.add(listener);
  return () => expiredListeners.delete(listener);
}

/**
 * Trades the refresh cookie for a new access token; resolves false if it's missing or
 * expired. Concurrent callers share one request, so a burst of 401s refreshes once.
 */
export function refreshSession(): Promise<boolean> {
  pendingRefresh ??= fetch(apiUrl('auth/refresh'), { method: 'POST', credentials: 'include' })
    .then(async (res) => {
      if (!res.ok) throw new Error(`refresh failed: ${res.status}`);
      const body: { access_token: string } = await res.json();
      setAccessToken(body.access_token);
      return true;
    })
    .catch(() => {
      setAccessToken(null);
      return false;
    })
    .finally(() => {
      pendingRefresh = null;
    });
  return pendingRefresh;
}

function withAuth(init: RequestInit | undefined, token: string | null): RequestInit {
  const headers = new Headers(init?.headers);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return { ...init, headers };
}

/**
 * `fetch` with the bearer token. On a 401 it refreshes the session once and retries;
 * if that fails too, it notifies `onSessionExpired` and returns the 401 response.
 */
export async function authFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const sentToken = accessToken;
  const res = await fetch(input, withAuth(init, sentToken));
  if (res.status !== 401) return res;

  // Another request may have renewed the token while this one was in flight.
  const renewed =
    (accessToken !== null && accessToken !== sentToken) || (await refreshSession());
  if (!renewed) {
    expiredListeners.forEach((listener) => listener());
    return res;
  }
  return fetch(input, withAuth(init, accessToken));
}
