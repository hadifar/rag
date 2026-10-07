import { useParams } from 'react-router-dom';
import { Composer, MessageList, WelcomePlaceholder, useChat } from '@/features/chat';
import { useOpenKbSource } from '@/features/knowledge-base';

export function ChatPage() {
  const { conversationId } = useParams();
  const { bubbles, isWaiting, showWelcome, sendMessage, attachments, retryBubbleId, retry } =
    useChat(conversationId);
  const openSource = useOpenKbSource();

  return (
    <div className="flex h-full flex-col">
      {showWelcome ? (
        <WelcomePlaceholder />
      ) : (
        <MessageList
          bubbles={bubbles}
          isWaiting={isWaiting}
          conversationId={conversationId}
          onOpenSource={openSource}
          retryBubbleId={retryBubbleId}
          onRetry={retry}
        />
      )}
      <Composer onSend={sendMessage} attachments={attachments} />
    </div>
  );
}
