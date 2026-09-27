import { memo, useEffect, useRef } from 'react';
import type { ChatMessage } from '../../types';
import { TextBubble } from './TextBubble';
import { ToolBubble } from './ToolBubble';
import { SourcesBubble } from './SourcesBubble';
import { TypingIndicator } from './TypingIndicator';

type MessageListProps = {
  messages: ChatMessage[];
  onOpenSource: (name: string) => void;
};

// Memoized: while an answer streams, only the bubble whose message changed re-renders
// (and re-parses its markdown), not every earlier one.
const MessageBubble = memo(function MessageBubble({
  message,
  onOpenSource,
}: {
  message: ChatMessage;
  onOpenSource: (name: string) => void;
}) {
  switch (message.type) {
    case 'typing':
      return <TypingIndicator />;

    case 'text':
      return <TextBubble {...message.content} position={message.position} />;

    case 'tool':
      return <ToolBubble {...message.content} />;

    case 'sources':
      return <SourcesBubble {...message.content} onOpen={onOpenSource} />;
  }
});

export function MessageList({ messages, onOpenSource }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' });
  }, [messages]);

  return (
    <div role="log" aria-label="Messages" className="flex-1 space-y-4 overflow-y-auto px-4 py-6">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.type === 'text' && message.position === 'right' ? 'justify-end' : 'justify-start'}`}
        >
          <MessageBubble message={message} onOpenSource={onOpenSource} />
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
