import { describe, expect, it } from 'vitest';

import { skillSuggestions } from '@/features/chat/model/skillCommand';

const skills = [
  { name: 'release-notes', description: '' },
  { name: 'review', description: '' },
  { name: 'tone', description: '' },
];

describe('skillSuggestions', () => {
  it('lists every skill for a bare /', () => {
    expect(skillSuggestions('/', skills)).toHaveLength(3);
  });

  it('keeps the skills whose name starts with what is typed', () => {
    expect(skillSuggestions('/re', skills).map((s) => s.name)).toEqual(['release-notes', 'review']);
  });

  it.each(['', 'hi', ' /re', '/re ', '/review this', 'x/re'])('suggests nothing for %j', (text) => {
    expect(skillSuggestions(text, skills)).toEqual([]);
  });
});
