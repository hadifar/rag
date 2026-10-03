import { api, unwrap } from '@/shared/api/client';

/** A knowledge-base document's file, e.g. one an answer cites. */
export function fetchKbSource(name: string): Promise<Blob> {
  return unwrap(
    api.GET('/api/retrieval/{filename}', { params: { path: { filename: name } }, parseAs: 'blob' })
  );
}
