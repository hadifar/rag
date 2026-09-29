import { describe, expect, it } from 'vitest';

import type { IngestionRunResponse } from '../../../src/types';
import { describeRun } from '../../../src/utils/ingestions';

function run(overrides: Partial<IngestionRunResponse>): IngestionRunResponse {
  return {
    id: 'r1',
    status: 'succeeded',
    started_at: '2026-09-28T10:00:00Z',
    finished_at: '2026-09-28T10:00:05Z',
    added: 0,
    updated: 0,
    unchanged: 0,
    removed: 0,
    error: null,
    ...overrides,
  };
}

describe('describeRun', () => {
  it('lists only the kinds of change that happened', () => {
    expect(describeRun(run({ added: 2, removed: 1, unchanged: 25 }))).toBe(
      '2 added, 1 removed (27 documents)',
    );
  });

  it('says so when nothing changed', () => {
    expect(describeRun(run({ unchanged: 1 }))).toBe('No changes (1 document)');
  });

  it("shows a failed run's error, and a running one as in progress", () => {
    expect(describeRun(run({ status: 'failed', error: 'not a zip file' }))).toBe('not a zip file');
    expect(describeRun(run({ status: 'running' }))).toBe('Indexing…');
  });
});
