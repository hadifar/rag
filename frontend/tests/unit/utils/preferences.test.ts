import { describe, expect, it } from 'vitest';

import { addPreferenceError, withPreference } from '@/features/preferences/model/preferences';

const dutch = { id: 'a', text: 'Answer in Dutch' };
const short = { id: 'b', text: 'Keep it short' };

describe('withPreference', () => {
  it('adds a new preference at the end', () => {
    expect(withPreference([dutch], short)).toEqual([dutch, short]);
  });

  it('keeps the list as it is for one already in it', () => {
    const list = [dutch, short];
    expect(withPreference(list, dutch)).toBe(list);
  });
});

describe('addPreferenceError', () => {
  it('says to remove one when the user is at the cap', () => {
    expect(addPreferenceError(409)).toMatch(/remove one first/);
  });

  it('asks for valid text when the server rejects it', () => {
    expect(addPreferenceError(400)).toMatch(/needs some text/);
    expect(addPreferenceError(422)).toMatch(/needs some text/);
  });

  it('falls back to a generic message otherwise', () => {
    expect(addPreferenceError(500)).toMatch(/Couldn't save/);
    expect(addPreferenceError(null)).toMatch(/Couldn't save/);
  });
});
