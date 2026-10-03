import { describe, expect, it } from 'vitest';

import { ApiError } from '@/shared/api/client';
import { loadStatus, shouldRetry } from '@/shared/api/queryClient';

describe('shouldRetry', () => {
  it('never retries a 4xx: it is the answer', () => {
    expect(shouldRetry(0, new ApiError(404, 'not found'))).toBe(false);
  });

  it('retries a 5xx or a network error twice', () => {
    expect(shouldRetry(0, new ApiError(503, 'unavailable'))).toBe(true);
    expect(shouldRetry(1, new TypeError('Failed to fetch'))).toBe(true);
    expect(shouldRetry(2, new TypeError('Failed to fetch'))).toBe(false);
  });
});

describe('loadStatus', () => {
  it('is ready while there is data, even after a failed refetch', () => {
    expect(loadStatus({ data: [], isError: true })).toBe('ready');
  });

  it('is loading, then error, until data arrives', () => {
    expect(loadStatus({ data: undefined, isError: false })).toBe('loading');
    expect(loadStatus({ data: undefined, isError: true })).toBe('error');
  });
});
