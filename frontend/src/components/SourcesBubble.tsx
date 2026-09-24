import type { SourcesContent } from '../types/chat';

export function SourcesBubble({ names }: SourcesContent) {
  return (
    <div className="max-w-[480px] rounded-xl bg-slate-50 px-3 py-2 text-sm">
      <div className="font-medium text-slate-700">📚 Sources</div>
      <ul className="mt-1 list-inside list-disc text-slate-600">
        {names.map((name) => (
          <li key={name}>
            <a
              href={`/api/kb/${name}`}
              target="_blank"
              rel="noreferrer"
              className="text-indigo-600 hover:underline"
            >
              {name}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
