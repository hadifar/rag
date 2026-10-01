import { memo, useEffect, useRef } from 'react';
import type { ChatMessage } from '../../types';
import { TextBubble } from './TextBubble';
import { ReasoningBubble } from './ReasoningBubble';
import { ToolBubble } from './ToolBubble';
import { TodosBubble } from './TodosBubble';
import { ReferencesBubble } from './ReferencesBubble';
import { TypingIndicator } from './TypingIndicator';

type MessageListProps = {
  messages: ChatMessage[];
  onOpenReference: (name: string) => void;
};

// Memoized: while an answer streams, only the bubble whose message changed re-renders
// (and re-parses its markdown), not every earlier one.
const MessageBubble = memo(function MessageBubble({
  message,
  onOpenReference,
}: {
  message: ChatMessage;
  onOpenReference: (name: string) => void;
}) {
  switch (message.type) {
    case 'typing':
      return <TypingIndicator />;

    case 'text':
      return <TextBubble {...message.content} position={message.position} />;

    case 'reasoning':
      return <ReasoningBubble {...message.content} />;

    case 'tool':
      return <ToolBubble {...message.content} />;

    case 'todos':
      return <TodosBubble {...message.content} />;

    case 'references':
      return <ReferencesBubble {...message.content} onOpen={onOpenReference} />;

    default:
      // A new bubble type fails to compile here until it's handled (see chatStream.ts).
      return message satisfies never;
  }
});

export function MessageList({ messages, onOpenReference }: MessageListProps) {
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
          <MessageBubble message={message} onOpenReference={onOpenReference} />
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
