import { useParams } from 'react-router-dom';
import { useChat } from '../hooks/useChat';
import { MessageList } from '../components/MessageList';
import { Composer } from '../components/Composer';

export default function ChatPage() {
  const { conversationId } = useParams();
  const { messages, sendMessage } = useChat(conversationId);

  return (
    <div className="flex h-full flex-col">
      <MessageList messages={messages} />
      <Composer onSend={sendMessage} />
    </div>
  );
}
