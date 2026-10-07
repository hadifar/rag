import type { SkillResponse } from '@/shared/types';

/** What the skill picker offers; the backend checks the frontmatter (rag/services/skill_service/parsing.py). */
export const SKILL_ACCEPT = '.md,.markdown';

export const UPLOAD_FAILED = "Couldn't upload this skill. Please try again.";

export function savedNotice(skill: SkillResponse): string {
  return `Saved skill “${skill.name}”. It's used when a question fits its description.`;
}

/** The list with `skill` added, or put in place of the one of its name, kept by name. */
export function withSkill(skills: SkillResponse[], skill: SkillResponse): SkillResponse[] {
  return [...skills.filter((s) => s.name !== skill.name), skill].sort((a, b) =>
    a.name < b.name ? -1 : a.name > b.name ? 1 : 0
  );
}
