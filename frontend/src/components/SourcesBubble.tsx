import type { SourcesContent } from '../types/chat';

export function SourcesBubble({ names }: SourcesContent) {
  return (
    <div className="sources-bubble">
      <div className="tool-bubble-title">📚 Sources</div>
      <ul>
        {names.map((name) => (
          <li key={name}>
            <a href={`/kb/${name}`} target="_blank" rel="noreferrer">
              {name}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
