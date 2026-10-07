import { describe, expect, it } from 'vitest';

import {
  MAX_SKILL_ARCHIVE_BYTES,
  MAX_SKILL_FILE_BYTES,
  fileCountLabel,
  skillUploadProblem,
  withSkill,
} from '@/features/skills/model/skills';
import type { SkillResponse } from '@/shared/types';

function skill(name: string, id = name, description = `About ${name}`, file_count = 0): SkillResponse {
  return { id, name, description, file_count, created_at: '', updated_at: '' };
}

describe('withSkill', () => {
  it('adds a new skill in name order', () => {
    expect(withSkill([skill('a'), skill('c')], skill('b')).map((s) => s.name)).toEqual(['a', 'b', 'c']);
  });

  it('replaces the skill of the same name', () => {
    const replaced = skill('a', 'a', 'New');

    expect(withSkill([skill('a'), skill('b')], replaced)).toEqual([replaced, skill('b')]);
  });
});

describe('skillUploadProblem', () => {
  it.each([
    ['SKILL.md', MAX_SKILL_FILE_BYTES],
    ['notes.MARKDOWN', MAX_SKILL_FILE_BYTES],
    ['bundle.zip', MAX_SKILL_ARCHIVE_BYTES],
    ['release-notes.skill', MAX_SKILL_ARCHIVE_BYTES],
  ])('accepts %s up to its limit', (name, limit) => {
    expect(skillUploadProblem({ name, size: limit })).toBeNull();
    expect(skillUploadProblem({ name, size: limit + 1 })).toBe(
      `This file is larger than ${limit / 1024} KB.`
    );
  });

  it('turns down any other kind of file', () => {
    expect(skillUploadProblem({ name: 'logo.png', size: 10 })).toMatch(/SKILL\.md file/);
  });
});

describe('fileCountLabel', () => {
  it('says how many reference files a skill has, if any', () => {
    expect(fileCountLabel(skill('a', 'a', '', 0))).toBeNull();
    expect(fileCountLabel(skill('a', 'a', '', 1))).toBe('1 reference file');
    expect(fileCountLabel(skill('a', 'a', '', 3))).toBe('3 reference files');
  });
});
