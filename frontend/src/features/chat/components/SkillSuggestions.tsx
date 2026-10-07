import type { SkillOption } from '../types';

type SkillSuggestionsProps = {
  /** The listbox's id, for the textarea's `aria-controls`. */
  id: string;
  /** An option's id, for the textarea's `aria-activedescendant`. */
  optionId: (index: number) => string;
  suggestions: SkillOption[];
  activeIndex: number;
  onPick: (index: number) => void;
};

/** The skills matching the "/" command being typed, above the composer. */
export function SkillSuggestions({ id, optionId, suggestions, activeIndex, onPick }: SkillSuggestionsProps) {
  return (
    <ul
      id={id}
      role="listbox"
      aria-label="Skills"
      className="absolute inset-x-0 bottom-full z-30 m-0 mb-2 max-h-64 list-none overflow-y-auto rounded-xl bg-white p-1.5 shadow-lg ring-1 ring-slate-900/10"
    >
      {suggestions.map((skill, index) => (
        <li
          key={skill.name}
          id={optionId(index)}
          role="option"
          aria-selected={index === activeIndex}
          // mousedown, not click: the textarea keeps its focus.
          onMouseDown={(e) => {
            e.preventDefault();
            onPick(index);
          }}
          className={`cursor-pointer rounded-lg px-2.5 py-2 ${index === activeIndex ? 'bg-slate-100' : ''}`}
        >
          <p className="m-0 font-mono text-[13px] text-slate-900">/{skill.name}</p>
          <p className="m-0 mt-0.5 truncate text-xs text-slate-500">{skill.description}</p>
        </li>
      ))}
    </ul>
  );
}
