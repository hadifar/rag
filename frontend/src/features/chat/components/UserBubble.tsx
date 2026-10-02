import type { TextContent } from '../types';

export function UserBubble({ text }: TextContent) {
  return (
    <div className="max-w-[480px] rounded-2xl rounded-tr-sm bg-slate-100 px-4 py-3">
      <p className="whitespace-pre-wrap text-sm leading-6 text-slate-800">{text}</p>
    </div>
  );
}
