import { useState } from 'react';

import { skillCommand, skillSuggestions } from '../model/skillCommand';
import type { SkillOption } from '../types';

/**
 * Suggests the user's skills while the message is a "/" command being typed: which are
 * shown, which is highlighted, and what the message becomes when one is picked. Escape
 * hides them until the text changes.
 */
export function useSkillCommand(text: string, skills: SkillOption[]) {
  const [active, setActive] = useState(0);
  const [dismissedAt, setDismissedAt] = useState<string | null>(null);
  const matches = dismissedAt === text ? [] : skillSuggestions(text, skills);
  // The highlight stays on a match as the list narrows.
  const activeIndex = Math.min(active, Math.max(matches.length - 1, 0));

  return {
    suggestions: matches,
    activeIndex,
    /** Moves the highlight by `step`, wrapping around. */
    move: (step: number) =>
      setActive((activeIndex + step + matches.length) % Math.max(matches.length, 1)),
    /** The message with the suggestion at `index` (default: the highlighted one) picked. */
    pick: (index = activeIndex): string => {
      setActive(0);
      const match = matches[index];
      return match ? skillCommand(match.name) : text;
    },
    dismiss: () => setDismissedAt(text),
  };
}
