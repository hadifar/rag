import { useParams } from 'react-router-dom';
import { SharedChatView, useSharedChat } from '@/features/chat';

/** A shared chat's public page: read-only, and open without signing in. */
export function SharedChatPage() {
  const { shareId } = useParams();
  return <SharedChatView {...useSharedChat(shareId!)} />;
}
