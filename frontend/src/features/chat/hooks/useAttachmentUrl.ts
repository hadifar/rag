import { useQuery } from '@tanstack/react-query';

import { fetchAttachment } from '../api/attachments';
import { chatKeys } from '../api/queryKeys';
import { readAsDataUrl } from './dataUrl';

/** A sent image, as a URL to show it: null while it loads, or if it couldn't be loaded. */
export function useAttachmentUrl(conversationId: string, attachmentId: string): string | null {
  const { data } = useQuery({
    queryKey: chatKeys.attachment(conversationId, attachmentId),
    queryFn: async ({ signal }) =>
      readAsDataUrl(await fetchAttachment(conversationId, attachmentId, signal)),
    // An attachment never changes.
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });
  return data ?? null;
}
