import type { SourcesContent } from '../types';

type SourcesBubbleProps = SourcesContent & { onOpen: (name: string) => void };

export function SourcesBubble({ sources, onOpen }: SourcesBubbleProps) {
  return (
    <div className="max-w-[480px] rounded-xl bg-slate-50 px-3 py-2 text-sm">
      <div className="font-medium text-slate-700">📚 Sources</div>
      <ul className="mt-1 list-inside list-disc text-slate-600">
        {sources.map((name) => (
          <li key={name}>
            <button
              type="button"
              onClick={() => onOpen(name)}
              className="text-indigo-600 hover:underline"
            >
              {name}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
