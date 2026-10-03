import { ApiError } from './client';

/**
 * What to tell the user about a failed call: the message for its status in `byStatus`,
 * else `fallback` (also for a network error, which has no status). Each feature words
 * its own messages; only it knows what, say, a 404 means for it.
 */
export function errorMessage(
  err: unknown,
  byStatus: Partial<Record<number, string>>,
  fallback: string
): string {
  return (err instanceof ApiError ? byStatus[err.status] : undefined) ?? fallback;
}

/** The status of a failed call, or null if it never got a response. */
export function errorStatus(err: unknown): number | null {
  return err instanceof ApiError ? err.status : null;
}

/** The backend's own reason for a failed call, fit to show as is; null if it gave none. */
export function errorDetail(err: unknown): string | null {
  return err instanceof ApiError ? err.detail : null;
}

/** Runs a delete, treating a 404 as done: it's idempotent, so already gone is success. */
export async function ignoreNotFound(call: Promise<unknown>): Promise<void> {
  try {
    await call;
  } catch (err) {
    if (!(err instanceof ApiError && err.status === 404)) throw err;
  }
}
