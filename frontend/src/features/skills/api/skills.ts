import { api, fileBody, unwrap } from '@/shared/api/client';
import type { SkillResponse } from '@/shared/types';

/** The user's skills, by name. */
export function fetchSkills(signal?: AbortSignal): Promise<SkillResponse[]> {
  return unwrap(api.GET('/api/skills', { signal }));
}

/**
 * Saves a SKILL.md file as a skill, replacing the user's skill of the same name. A rejected
 * file throws an `ApiError` whose `detail` is the backend's reason (e.g. no frontmatter),
 * fit to show as is.
 */
export function uploadSkill(file: File): Promise<SkillResponse> {
  return unwrap(api.POST('/api/skills', fileBody(file)));
}

export async function deleteSkill(skillId: string): Promise<void> {
  await unwrap(api.DELETE('/api/skills/{skill_id}', { params: { path: { skill_id: skillId } } }));
}
