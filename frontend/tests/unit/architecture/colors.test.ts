import { describe, expect, it } from 'vitest';

// Colours go by role (`primary`, `danger`, `success`, `warning`, defined in index.css), with
// Tailwind's `slate` for neutrals; any other palette is a hard-coded colour a rebrand misses.
const PALETTES =
  'red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|gray|zinc|neutral|stone';
const HARD_CODED = new RegExp(`[\\w:-]*-(?:${PALETTES})-\\d{2,3}\\b`, 'g');

const sources = import.meta.glob<string>('/src/**/*.{ts,tsx}', {
  query: '?raw',
  import: 'default',
  eager: true,
});

describe('colours', () => {
  it('come from the theme tokens, never a Tailwind palette other than slate', () => {
    expect(Object.keys(sources).length).toBeGreaterThan(10); // the glob found the app
    const found = Object.entries(sources).flatMap(([file, text]) =>
      [...text.matchAll(HARD_CODED)].map((m) => `${file}: ${m[0]}`)
    );
    expect(found).toEqual([]);
  });
});
