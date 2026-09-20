import Chat from '@chatui/core';
import { useChat } from './hooks/useChat';
import { renderMessageContent } from './components/MessageContent';
import { EmptyState } from './components/EmptyState';
import './App.css';

function App() {
  const { messages, isTyping, newChat, sendMessage } = useChat();

  return (
    <Chat
      locale="en-US"
      navbar={{
        title: 'RAG',
        rightContent: [{ label: 'New chat', onClick: newChat }],
      }}
      placeholder="Type a message..."
      messages={messages}
      renderBeforeMessageList={() => (messages.length === 0 ? <EmptyState /> : null)}
      renderMessageContent={renderMessageContent}
      isTyping={isTyping}
      onSend={sendMessage}
    />
  );
}

export default App;
