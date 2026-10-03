import { api, apiError, apiUrl, authFetch, unwrap } from '@/shared/api/client';
import type { IngestionRunResponse } from '@/shared/types';

/**
 * Uploads a knowledge-base .zip; resolves with the new `running` run. A rejected upload
 * throws an `ApiError` whose `detail` is the backend's reason (e.g. not a zip, another
 * upload still running), fit to show as is. Sent as form data, so through `authFetch`:
 * the schema describes the file as a string, which the typed client would send as JSON.
 */
export async function uploadKnowledgeBase(file: File): Promise<IngestionRunResponse> {
  const body = new FormData();
  body.append('file', file);
  const res = await authFetch(apiUrl('ingestions'), { method: 'POST', body });
  if (!res.ok) throw await apiError(res, 'POST /api/ingestions');
  return res.json();
}

export function fetchIngestionRun(id: string): Promise<IngestionRunResponse> {
  return unwrap(api.GET('/api/ingestions/{run_id}', { params: { path: { run_id: id } } }));
}

/** The most recent run, or null if nothing was ever uploaded. */
export function fetchLatestIngestionRun(
  signal?: AbortSignal
): Promise<IngestionRunResponse | null> {
  return unwrap(api.GET('/api/ingestions/latest', { signal }));
}
