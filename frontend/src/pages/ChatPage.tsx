import { useLocation } from 'react-router-dom';
import { useChat } from '../hooks/useChat';
import { MessageList } from '../components/MessageList';
import { Composer } from '../components/Composer';

export default function ChatPage() {
  const { key } = useLocation();
  const { messages, sendMessage } = useChat();

  return (
    <div key={key} className="flex h-full flex-col">
      <MessageList messages={messages} />
      <Composer onSend={sendMessage} />
    </div>
  );
}
