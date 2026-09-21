import Chat from '@chatui/core';
import { useChat } from './hooks/useChat';
import { renderMessageContent } from './components/MessageContent';
import { EmptyState } from './components/EmptyState';

import './App.css';

function App() {
  const { messages, isTyping, sendMessage } = useChat();

  // const defaultQuickReplies = [
  //   {
  //     name: 'What is your name?',
  //   },
  //   {
  //     name: 'Tell me a joke.',
  //   },
  //   {
  //     name: 'How to cook pasta?',
  //   },
  // ];

  return (
    <Chat
      locale="en-US"
      navbar={{ title: 'RAG' }}
      placeholder="Type a message..."
      messages={messages}
      renderBeforeMessageList={() => (messages.length === 0 ? <EmptyState /> : null)}
      renderMessageContent={renderMessageContent}
      // quickReplies={defaultQuickReplies}
      // onQuickReplyClick={(item: QuickReplyItemProps) => sendMessage('text', item.name)}
      isTyping={isTyping}
      onSend={sendMessage}
    />
  );
}

export default App;
