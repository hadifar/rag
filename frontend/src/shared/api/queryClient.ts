import { QueryClient } from '@tanstack/react-query';

import type { LoadStatus } from '@/shared/types';
import { ApiError } from './client';

const MAX_RETRIES = 2;

/**
 * Retries a failed load only when trying again can help: a network error or a 5xx. A 4xx
 * is the answer (a 401 was already refreshed by `authFetch`, a 404 won't appear later).
 */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status < 500) return false;
  return failureCount < MAX_RETRIES;
}

export function createQueryClient(): QueryClient {
  return new QueryClient({ defaultOptions: { queries: { retry: shouldRetry } } });
}

/**
 * Where a query's load stands, for the UI. Data on hand is `ready` even if a later
 * refetch (or "load more") failed: what's shown is still right.
 */
export function loadStatus(query: { data: unknown; isError: boolean }): LoadStatus {
  if (query.data !== undefined) return 'ready';
  return query.isError ? 'error' : 'loading';
}
