import type { SourcesContent } from '../types';
import { BubbleFrame } from './BubbleFrame';

type SourcesBubbleProps = SourcesContent & { onOpen: (name: string) => void };

export function SourcesBubble({ sources, onOpen }: SourcesBubbleProps) {
  if (sources.length === 0) {
    return (
      <BubbleFrame look="card">
        <span className="font-medium text-slate-700">📚 Sources</span>
        <span className="text-slate-500"> — none found</span>
      </BubbleFrame>
    );
  }

  return (
    <BubbleFrame look="card">
      <div className="font-medium text-slate-700">📚 Sources</div>
      <ul className="mt-1 list-inside list-disc text-slate-600">
        {sources.map((name) => (
          <li key={name}>
            <button
              type="button"
              onClick={() => onOpen(name)}
              className="text-primary-600 hover:underline"
            >
              {name}
            </button>
          </li>
        ))}
      </ul>
    </BubbleFrame>
  );
}
