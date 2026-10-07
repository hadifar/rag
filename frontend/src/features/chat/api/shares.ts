import { publicApi, unwrap } from '@/shared/api/client';
import type { SharedConversationResponse } from '@/shared/types';

/**
 * A shared conversation as it was when shared. Through `publicApi`: a share link is
 * read without signing in, so there's no session to send or renew.
 */
export function fetchSharedConversation(
  shareId: string,
  signal?: AbortSignal
): Promise<SharedConversationResponse> {
  return unwrap(
    publicApi.GET('/api/shares/{share_id}', { params: { path: { share_id: shareId } }, signal })
  );
}
