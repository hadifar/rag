import { useParams } from 'react-router-dom';
import { useChat } from '../hooks/useChat';
import { MessageList } from '../components/chat/MessageList';
import { Composer } from '../components/chat/Composer';

export function ChatPage() {
  const { conversationId } = useParams();
  const { messages, sendMessage, openSource } = useChat(conversationId);

  return (
    <div className="flex h-full flex-col">
      <MessageList messages={messages} onOpenSource={openSource} />
      <Composer onSend={sendMessage} />
    </div>
  );
}
