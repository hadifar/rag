import { memo, useEffect, useRef, type ComponentType } from 'react';
import type { Bubble, BubbleOf, BubbleType } from '../types';
import { ErrorBubble } from './ErrorBubble';
import { ReasoningBubble } from './ReasoningBubble';
import { ReferencesBubble } from './ReferencesBubble';
import { TextBubble } from './TextBubble';
import { TodosBubble } from './TodosBubble';
import { ToolBubble } from './ToolBubble';
import { TypingIndicator } from './TypingIndicator';
import { UserBubble } from './UserBubble';
import { VerificationBubble } from './VerificationBubble';

type BubbleViewProps<K extends BubbleType> = {
  bubble: BubbleOf<K>;
  onOpenReference: (name: string) => void;
  onRetry?: () => void;
};

// Which component shows each bubble type. A new type fails to compile here until it has
// one (see model/transcript.ts for where bubbles come from).
const bubbleViews: { [K in BubbleType]: ComponentType<BubbleViewProps<K>> } = {
  user: ({ bubble }) => <UserBubble {...bubble.content} />,
  text: ({ bubble }) => <TextBubble {...bubble.content} />,
  reasoning: ({ bubble }) => <ReasoningBubble {...bubble.content} />,
  tool: ({ bubble }) => <ToolBubble {...bubble.content} />,
  todos: ({ bubble }) => <TodosBubble {...bubble.content} />,
  verification: ({ bubble }) => <VerificationBubble {...bubble.content} />,
  references: ({ bubble, onOpenReference }) => (
    <ReferencesBubble {...bubble.content} onOpen={onOpenReference} />
  ),
  error: ({ bubble, onRetry }) => <ErrorBubble {...bubble.content} onRetry={onRetry} />,
};

// Memoized: while an answer streams, only the bubble whose content changed re-renders
// (and re-parses its markdown), not every earlier one.
const MessageBubble = memo(function MessageBubble({ bubble, onOpenReference, onRetry }: BubbleViewProps<BubbleType>) {
  // The map pairs each type with its own view; TypeScript can't follow that through a lookup.
  const View = bubbleViews[bubble.type] as ComponentType<BubbleViewProps<BubbleType>>;
  return <View bubble={bubble} onOpenReference={onOpenReference} onRetry={onRetry} />;
});

type MessageListProps = {
  bubbles: Bubble[];
  isWaiting: boolean;
  onOpenReference: (name: string) => void;
  /** The error bubble that offers a retry, if any, and what retrying does. */
  retryBubbleId: string | null;
  onRetry: () => void;
};

export function MessageList({ bubbles, isWaiting, onOpenReference, retryBubbleId, onRetry }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' });
  }, [bubbles, isWaiting]);

  return (
    <div role="log" aria-label="Messages" className="flex-1 space-y-4 overflow-y-auto px-4 py-6">
      {bubbles.map((bubble) => (
        <div
          key={bubble.id}
          className={`flex ${bubble.type === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <MessageBubble
            bubble={bubble}
            onOpenReference={onOpenReference}
            onRetry={bubble.id === retryBubbleId ? onRetry : undefined}
          />
        </div>
      ))}
      {isWaiting && (
        <div className="flex justify-start">
          <TypingIndicator />
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
