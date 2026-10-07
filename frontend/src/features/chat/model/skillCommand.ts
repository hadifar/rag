import type { SkillOption } from '../types';

// The message so far is a skill command still being typed: "/" and the start of a name.
// The backend reads the command (rag/services/agent_service/skills.py).
const TYPING_COMMAND = /^\/([a-z0-9-]*)$/;

/** The skills whose name starts with the command being typed; none if it isn't one. */
export function skillSuggestions(text: string, skills: SkillOption[]): SkillOption[] {
  const typed = TYPING_COMMAND.exec(text)?.[1];
  if (typed === undefined) return [];
  return skills.filter((s) => s.name.startsWith(typed));
}

/** The message once a suggestion is picked: its command, ready for the rest. */
export function skillCommand(name: string): string {
  return `/${name} `;
}
