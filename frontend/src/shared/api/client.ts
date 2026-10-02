import createClient from 'openapi-fetch';

import type { ApiPaths, TokenResponse } from '@/shared/types';

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

/** Every failed API call throws this, so callers can branch on `status` (e.g. a 404). */
export class ApiError extends Error {
  readonly status: number;
  /** The backend's own reason (FastAPI's `detail`), fit to show as is; null if it sent none. */
  readonly detail: string | null;

  constructor(status: number, message: string, detail: string | null = null) {
    super(detail ?? message);
    this.status = status;
    this.detail = detail;
  }
}

/** FastAPI's `{"detail": "..."}`; null for anything else (e.g. nginx's own HTML error page). */
function detailOf(body: unknown): string | null {
  if (body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string') {
    return body.detail;
  }
  return null;
}

/** The `ApiError` for a failed response, with the backend's reason if it gave one. */
export async function apiError(res: Response, what: string): Promise<ApiError> {
  const body: unknown = await res.json().catch(() => null);
  return new ApiError(res.status, `${what} failed: ${res.status}`, detailOf(body));
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
      const body: TokenResponse = await res.json();
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

/** Sends `input` with the bearer token. A `Request` is sent as a copy: its body can be read once. */
function send(input: RequestInfo | URL, init: RequestInit | undefined, token: string | null) {
  if (input instanceof Request) {
    const request = input.clone();
    if (token) request.headers.set('Authorization', `Bearer ${token}`);
    return fetch(request);
  }
  const headers = new Headers(init?.headers);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return fetch(input, { ...init, headers });
}

/**
 * `fetch` with the bearer token. On a 401 it refreshes the session once and retries;
 * if that fails too, it notifies `onSessionExpired` and returns the 401 response.
 */
export async function authFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const sentToken = accessToken;
  const res = await send(input, init, sentToken);
  if (res.status !== 401) return res;

  // Another request may have renewed the token while this one was in flight.
  const renewed =
    (accessToken !== null && accessToken !== sentToken) || (await refreshSession());
  if (!renewed) {
    expiredListeners.forEach((listener) => listener());
    return res;
  }
  return send(input, init, accessToken);
}

/**
 * The backend, typed from its OpenAPI schema: each call's path, parameters, body and
 * response are checked against `ApiPaths`, so a renamed route or field fails `tsc`. Every
 * call goes through `authFetch`. Wrap a call in `unwrap` to get its data or an `ApiError`.
 */
export const api = createClient<ApiPaths>({
  // Absolute: the client builds a `Request`, which can't take a relative URL everywhere.
  baseUrl: window.location.origin,
  fetch: authFetch,
});

/** A typed call's data; throws an `ApiError` (with the backend's `detail`) if it failed. */
export async function unwrap<T>(
  call: Promise<{ data?: T; error?: unknown; response: Response }>
): Promise<T> {
  const { data, error, response } = await call;
  if (!response.ok) {
    const what = `${response.url.replace(window.location.origin, '')}`;
    throw new ApiError(response.status, `${what} failed: ${response.status}`, detailOf(error));
  }
  return data as T;
}
