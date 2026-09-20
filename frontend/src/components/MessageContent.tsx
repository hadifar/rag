import { Bubble, TypingBubble, type MessageProps } from '@chatui/core';
import { ToolBubble } from './ToolBubble';
import { SourcesBubble } from './SourcesBubble';
import type { TextContent, ToolContent, SourcesContent } from '../types/chat';

export function renderMessageContent(msg: MessageProps) {
  switch (msg.type) {
    case 'text': {
      const { text } = msg.content as TextContent;
      return msg.position === 'right' ? (
        <Bubble content={text} />
      ) : (
        <TypingBubble content={text} options={{ interval: 15, step: [2, 5] }} />
      );
    }
    case 'tool':
      return <ToolBubble {...(msg.content as ToolContent)} />;
    case 'sources':
      return <SourcesBubble {...(msg.content as SourcesContent)} />;
    default:
      return null;
  }
}
