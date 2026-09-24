import Chat from '@chatui/core';
import { useLocation } from 'react-router-dom';
import { useChat } from '../hooks/useChat';
import { renderMessageContent } from '../components/MessageContent';


import '../App.css';


export default function ChatPage() {
  const { key } = useLocation();
  const { messages, sendMessage } = useChat();

  return <Chat
    key={key}
    locale="en-US"
    placeholder="Type a message..."
    messages={messages}
    renderMessageContent={renderMessageContent}
    onSend={sendMessage}
  />;

}
