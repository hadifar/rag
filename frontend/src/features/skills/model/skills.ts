import type { SkillResponse } from '@/shared/types';

/** What the skill picker offers; the backend checks the content (rag/services/skill_service/). */
export const SKILL_ACCEPT = '.md,.markdown,.zip,.skill';

// Keep in sync with UPLOADS__SKILL_MAX_BYTES and UPLOADS__SKILL_ARCHIVE_MAX_BYTES (rag/config/uploads.py).
export const MAX_SKILL_FILE_BYTES = 50 * 1024;
export const MAX_SKILL_ARCHIVE_BYTES = 512 * 1024;

export const UPLOAD_FAILED = "Couldn't upload this skill. Please try again.";

const MARKDOWN = /\.(md|markdown)$/i;
const ARCHIVE = /\.(zip|skill)$/i;

/** Why `file` can't be uploaded as a skill, before it's sent; null if it can be. */
export function skillUploadProblem(file: { name: string; size: number }): string | null {
  const limit = MARKDOWN.test(file.name)
    ? MAX_SKILL_FILE_BYTES
    : ARCHIVE.test(file.name)
      ? MAX_SKILL_ARCHIVE_BYTES
      : null;
  if (limit === null) return 'Upload a SKILL.md file, or a .zip or .skill archive holding one.';
  if (file.size > limit) return `This file is larger than ${limit / 1024} KB.`;
  return null;
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
