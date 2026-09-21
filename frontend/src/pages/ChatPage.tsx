import Chat from '@chatui/core';
import { useChat } from '../hooks/useChat';
import { renderMessageContent } from '../components/MessageContent';


import '../App.css';

export default function ChatPage() {
  const { messages, sendMessage } = useChat();

  return (
    <Chat
      locale="en-US"
      placeholder="Type a message..."
      messages={messages}

      renderMessageContent={renderMessageContent}
      onSend={sendMessage}
    />
  );
}
