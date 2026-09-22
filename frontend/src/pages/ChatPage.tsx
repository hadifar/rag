import Chat from '@chatui/core';
import { useLocation } from 'react-router-dom';
import { useChat } from '../hooks/useChat';
import { renderMessageContent } from '../components/MessageContent';


import '../App.css';

function ChatSession() {
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

// New-chat navigates to '/' again, which produces a fresh location.key;
// keying the session on it remounts the chat with empty state.
export default function ChatPage() {
  const { key } = useLocation();
  return <ChatSession key={key} />;
}
