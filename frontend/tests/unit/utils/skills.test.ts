import { describe, expect, it } from 'vitest';

import {
  fileCountLabel,
  skillSizes,
  skillUploadProblem,
  withSkill,
} from '@/features/skills/model/skills';
import { sizeLabel } from '@/shared/sizes';
import type { SkillResponse } from '@/shared/types';

const LIMITS = { skill_max_bytes: 50 * 1024, skill_archive_max_bytes: 512 * 1024 };

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
    ['SKILL.md', LIMITS.skill_max_bytes, '50 KB'],
    ['notes.MARKDOWN', LIMITS.skill_max_bytes, '50 KB'],
    ['bundle.zip', LIMITS.skill_archive_max_bytes, '512 KB'],
    ['release-notes.skill', LIMITS.skill_archive_max_bytes, '512 KB'],
  ])('accepts %s up to its limit', (name, limit, label) => {
    expect(skillUploadProblem({ name, size: limit }, LIMITS)).toBeNull();
    expect(skillUploadProblem({ name, size: limit + 1 }, LIMITS)).toBe(
      `This file is larger than ${label}.`
    );
  });

  it('leaves the size to the backend until the limits are known', () => {
    expect(skillUploadProblem({ name: 'SKILL.md', size: 10 ** 9 }, null)).toBeNull();
  });

  it('turns down any other kind of file', () => {
    expect(skillUploadProblem({ name: 'logo.png', size: 10 }, LIMITS)).toMatch(/SKILL\.md file/);
  });
});

describe('skillSizes', () => {
  it('words each limit, once known', () => {
    expect(skillSizes(LIMITS)).toEqual({ file: '50 KB', archive: '512 KB' });
    expect(skillSizes(null)).toBeNull();
  });
});

describe('sizeLabel', () => {
  it.each([
    [20 * 1024 * 1024, '20 MB'],
    [1.5 * 1024 * 1024, '1.5 MB'],
    [512 * 1024, '512 KB'],
    [51_200, '50 KB'],
  ])('words %i bytes as %s', (bytes, label) => {
    expect(sizeLabel(bytes)).toBe(label);
  });
});

describe('fileCountLabel', () => {
  it('says how many reference files a skill has, if any', () => {
    expect(fileCountLabel(skill('a', 'a', '', 0))).toBeNull();
    expect(fileCountLabel(skill('a', 'a', '', 1))).toBe('1 reference file');
    expect(fileCountLabel(skill('a', 'a', '', 3))).toBe('3 reference files');
  });
});
