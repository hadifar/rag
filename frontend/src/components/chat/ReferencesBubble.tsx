import type { ReferencesContent } from '../../types';

type ReferencesBubbleProps = ReferencesContent & { onOpen: (name: string) => void };

export function ReferencesBubble({ references, onOpen }: ReferencesBubbleProps) {
  if (references.length === 0) {
    return (
      <div className="max-w-[480px] rounded-xl bg-slate-50 px-3 py-2 text-sm">
        <span className="font-medium text-slate-700">📚 Sources</span>
        <span className="text-slate-500"> — none found</span>
      </div>
    );
  }

  return (
    <div className="max-w-[480px] rounded-xl bg-slate-50 px-3 py-2 text-sm">
      <div className="font-medium text-slate-700">📚 Sources</div>
      <ul className="mt-1 list-inside list-disc text-slate-600">
        {references.map((name) => (
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
