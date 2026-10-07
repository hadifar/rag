import { sizeLabel } from '@/shared/sizes';
import type { SkillResponse, UploadLimitsResponse } from '@/shared/types';

/** What the skill picker offers; the backend checks the content (rag/services/skill_service/). */
export const SKILL_ACCEPT = '.md,.markdown,.zip,.skill';

/** The largest skill files the backend takes, in bytes. */
export type SkillLimits = Pick<UploadLimitsResponse, 'skill_max_bytes' | 'skill_archive_max_bytes'>;

export const UPLOAD_FAILED = "Couldn't upload this skill. Please try again.";

const MARKDOWN = /\.(md|markdown)$/i;
const ARCHIVE = /\.(zip|skill)$/i;

/**
 * Why `file` can't be uploaded as a skill, before it's sent; null if it can be. Its size
 * is checked once the `limits` are known; until then the backend checks it alone.
 */
export function skillUploadProblem(
  file: { name: string; size: number },
  limits: SkillLimits | null
): string | null {
  const isMarkdown = MARKDOWN.test(file.name);
  if (!isMarkdown && !ARCHIVE.test(file.name)) {
    return 'Upload a SKILL.md file, or a .zip or .skill archive holding one.';
  }
  if (limits === null) return null;
  const limit = isMarkdown ? limits.skill_max_bytes : limits.skill_archive_max_bytes;
  return file.size > limit ? `This file is larger than ${sizeLabel(limit)}.` : null;
}

/** How large each kind of skill upload may be, to tell the user; null until known. */
export function skillSizes(limits: SkillLimits | null): { file: string; archive: string } | null {
  if (limits === null) return null;
  return { file: sizeLabel(limits.skill_max_bytes), archive: sizeLabel(limits.skill_archive_max_bytes) };
}

export function savedNotice(skill: SkillResponse): string {
  return `Saved skill “${skill.name}”. It's used when a question fits its description.`;
}

/** How many reference files a skill has, to show beside it; null if none. */
export function fileCountLabel(skill: SkillResponse): string | null {
  if (skill.file_count === 0) return null;
  return skill.file_count === 1 ? '1 reference file' : `${skill.file_count} reference files`;
}

/** The list with `skill` added, or put in place of the one of its name, kept by name. */
export function withSkill(skills: SkillResponse[], skill: SkillResponse): SkillResponse[] {
  return [...skills.filter((s) => s.name !== skill.name), skill].sort((a, b) =>
    a.name < b.name ? -1 : a.name > b.name ? 1 : 0
  );
}
