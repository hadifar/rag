import type { TextContent } from '../types/chat';

type TextBubbleProps = TextContent & { position?: 'left' | 'right' };

export function TextBubble({ text, position }: TextBubbleProps) {
  if (position === 'right') {
    return (
      <div className="max-w-[480px] rounded-2xl rounded-tr-sm bg-slate-100 px-4 py-3">
        <p className="whitespace-pre-wrap text-sm leading-6 text-slate-800">{text}</p>
      </div>
    );
  }

  return (
    <p className="max-w-[480px] whitespace-pre-wrap px-3 text-sm leading-6 text-slate-800">
      {text}
    </p>
  );
}
