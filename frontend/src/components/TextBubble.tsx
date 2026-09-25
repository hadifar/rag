import Markdown, { type Components } from 'react-markdown';
import remarkBreaks from 'remark-breaks';
import type { TextContent } from '../types/chat';

type TextBubbleProps = TextContent & { position?: 'left' | 'right' };

// react-markdown no longer tells us whether a `code` node is inline or a
// fenced block, so we tell them apart the same way the content itself does:
// a fenced block's text always contains a newline, an inline span never does.
const Code: Components['code'] = ({ className, children }) => {
  if (typeof children === 'string' && children.includes('\n')) {
    return (
      <pre className="overflow-x-auto rounded-lg bg-slate-900 p-3 text-slate-100">
        <code className={className}>{children}</code>
      </pre>
    );
  }
  return <code className="rounded bg-slate-200 px-1 py-0.5 text-[13px]">{children}</code>;
};

export function TextBubble({ text, position }: TextBubbleProps) {
  // user
  if (position === 'right') {
    return (
      <div className="max-w-[480px] rounded-2xl rounded-tr-sm bg-slate-100 px-4 py-3">
        <p className="whitespace-pre-wrap text-sm leading-6 text-slate-800">{text}</p>
      </div>
    );
  }
  // assistant
  return (
    <div className="max-w-[480px] px-3 text-sm leading-6 text-slate-800">
      <Markdown
        remarkPlugins={[remarkBreaks]}
        components={{
          p: ({ children }) => <p className="whitespace-pre-wrap">{children}</p>,
          pre: ({ children }) => <>{children}</>,
          code: Code,
        }}
      >
        {text}
      </Markdown>
    </div>
  );
}
