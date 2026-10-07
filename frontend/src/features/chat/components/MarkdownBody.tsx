import Markdown, { type Components } from 'react-markdown';
import remarkBreaks from 'remark-breaks';
import { isFencedCodeBlock } from '../model/markdown';

const Code: Components['code'] = ({ className, children }) => {
  if (isFencedCodeBlock(children)) {
    return (
      <pre className="overflow-x-auto rounded-lg bg-slate-900 p-3 text-slate-100">
        <code className={className}>{children}</code>
      </pre>
    );
  }
  return <code className="rounded bg-slate-200 px-1 py-0.5 text-[13px]">{children}</code>;
};

// Module-level so they keep one identity: components created during render would be
// new types every time, remounting the whole answer on each streamed chunk.
const markdownComponents: Components = {
  p: ({ children }) => <p className="whitespace-pre-wrap">{children}</p>,
  pre: ({ children }) => <>{children}</>,
  code: Code,
};
const remarkPlugins = [remarkBreaks];

/** Markdown text, styled for a chat bubble. */
export function MarkdownBody({ text }: { text: string }) {
  return (
    <Markdown remarkPlugins={remarkPlugins} components={markdownComponents}>
      {text}
    </Markdown>
  );
}
