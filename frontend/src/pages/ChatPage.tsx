import { useParams } from 'react-router-dom';
import { useChat } from '../hooks/useChat';
import { MessageList } from '../components/chat/MessageList';
import { Composer } from '../components/chat/Composer';
import { WelcomePlaceholder } from '../components/chat/WelcomePlaceholder';

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
