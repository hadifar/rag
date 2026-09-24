import { useEffect, useRef } from 'react';
import type { ChatMessage } from '../types/chat';
import { ToolBubble } from './ToolBubble';
import { SourcesBubble } from './SourcesBubble';
import { TypingIndicator } from './TypingIndicator';

function MessageBubble({ message }: { message: ChatMessage }) {
  switch (message.type) {
    case 'typing':
      return <TypingIndicator />;

    case 'text':
      return message.position === 'right' ? (
        <div className="max-w-[480px] rounded-2xl rounded-tr-sm bg-slate-100 px-4 py-3">
          <p className="whitespace-pre-wrap text-sm leading-6 text-slate-800">
            {message.content.text}
          </p>
        </div>
      ) : (
        <p className="max-w-[480px] whitespace-pre-wrap text-sm leading-6 text-slate-800">
          {message.content.text}
        </p>
      );

    case 'tool':
      return <ToolBubble {...message.content} />;

    case 'sources':
      return <SourcesBubble {...message.content} />;
  }
}

export function MessageList({ messages }: { messages: ChatMessage[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' });
  }, [messages]);

  return (
    <div className="flex-1 space-y-4 overflow-y-auto px-4 py-6">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.type === 'text' && message.position === 'right' ? 'justify-end' : 'justify-start'}`}
        >
          <MessageBubble message={message} />
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
