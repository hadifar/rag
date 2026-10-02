import { useParams } from 'react-router-dom';
import { Composer, MessageList, WelcomePlaceholder, useChat } from '@/features/chat';

export function ChatPage() {
  const { conversationId } = useParams();
  const { messages, showWelcome, sendMessage, openReference } = useChat(conversationId);

  return (
    <div className="flex h-full flex-col">
      {showWelcome ? (
        <WelcomePlaceholder />
      ) : (
        <MessageList messages={messages} onOpenReference={openReference} />
      )}
      <Composer onSend={sendMessage} />
    </div>
  );
}
