import { api, fileBody, unwrap } from '@/shared/api/client';
import type { IngestionRunResponse } from '@/shared/types';

/**
 * Uploads a knowledge-base .zip; resolves with the new `running` run. A rejected upload
 * throws an `ApiError` whose `detail` is the backend's reason (e.g. not a zip, another
 * upload still running), fit to show as is.
 */
export function uploadKnowledgeBase(file: File): Promise<IngestionRunResponse> {
  return unwrap(api.POST('/api/ingestions', fileBody(file)));
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
