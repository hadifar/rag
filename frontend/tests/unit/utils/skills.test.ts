import { describe, expect, it } from 'vitest';

import { withSkill } from '@/features/skills/model/skills';
import type { SkillResponse } from '@/shared/types';

function skill(name: string, id = name, description = `About ${name}`): SkillResponse {
  return { id, name, description, created_at: '', updated_at: '' };
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
