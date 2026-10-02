/** The cache keys of ingestion data; the one place they're spelled. */
export const ingestionKeys = {
  latest: ['ingestions', 'latest'] as const,
  run: (id: string | undefined) => ['ingestions', 'run', id] as const,
};
