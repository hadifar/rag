import { ApiError, apiUrl, authFetch, requestJson } from './client';
import type { IngestionRunResponse } from '../types';

// nginx answers these itself (as HTML), before the backend's JSON `detail` exists.
const FALLBACK_MESSAGES: Record<number, string> = {
  413: 'The file is larger than 20 MB.',
  429: 'Too many requests; wait a moment and try again.',
};

/**
 * Uploads a knowledge-base .zip; resolves with the new `running` run. A rejected upload
 * throws an `ApiError` whose message is the backend's reason (e.g. not a zip, another
 * upload still running), fit to show as is.
 */
export async function uploadKnowledgeBase(file: File): Promise<IngestionRunResponse> {
  const body = new FormData();
  body.append('file', file);
  const res = await authFetch(apiUrl('ingestions'), { method: 'POST', body });
  if (!res.ok) throw new ApiError(res.status, await errorMessage(res));
  return res.json();
}

export function fetchIngestionRun(id: string): Promise<IngestionRunResponse> {
  return requestJson(`ingestions/${encodeURIComponent(id)}`);
}

/** The most recent run, or null if nothing was ever uploaded. */
export function fetchLatestIngestionRun(
  signal?: AbortSignal
): Promise<IngestionRunResponse | null> {
  return requestJson('ingestions/latest', { signal });
}

async function errorMessage(res: Response): Promise<string> {
  const body: unknown = await res.json().catch(() => null);
  if (body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string') {
    return body.detail;
  }
  return FALLBACK_MESSAGES[res.status] ?? `Upload failed (${res.status}).`;
}
