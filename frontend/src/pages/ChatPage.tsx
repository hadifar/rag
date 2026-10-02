import { useParams } from 'react-router-dom';
import { Composer, MessageList, WelcomePlaceholder, useChat } from '@/features/chat';
import { useOpenKbSource } from '@/features/knowledge-base';

export function ChatPage() {
  const { conversationId } = useParams();
  const { bubbles, isWaiting, showWelcome, sendMessage } = useChat(conversationId);
  const openReference = useOpenKbSource();

  return (
    <div className="flex h-full flex-col">
      {showWelcome ? (
        <WelcomePlaceholder />
      ) : (
        <MessageList bubbles={bubbles} isWaiting={isWaiting} onOpenReference={openReference} />
      )}
      <Composer onSend={sendMessage} />
    </div>
  );
}
