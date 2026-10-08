import type { SourcesContent } from '../types';
import { BubbleFrame } from './BubbleFrame';

/** Without `onOpen` (a shared chat, read signed out), each source is a plain name. */
type SourcesBubbleProps = SourcesContent & { onOpen?: (name: string) => void };

export function SourcesBubble({ sources, onOpen }: SourcesBubbleProps) {
  if (sources.length === 0) {
    return (
      <BubbleFrame look="card">
        <span className="text-xs font-medium text-slate-700">📚 Sources</span>
        <span className="text-xs text-slate-500"> — none found</span>
      </BubbleFrame>
    );
  }

  return (
    <BubbleFrame look="card">
      <div className="text-xs font-medium text-slate-700">📚 Sources</div>
      <ul className="mt-1 list-inside list-disc text-xs text-slate-600">
        {sources.map((name) => (
          <li key={name}>
            {onOpen ? (
              <button
                type="button"
                onClick={() => onOpen(name)}
                className="text-xs text-primary-600 hover:underline"
              >
                {name}
              </button>
            ) : (
              name
            )}
          </li>
        ))}
      </ul>
    </BubbleFrame>
  );
}
