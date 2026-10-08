/** The cache keys of settings data; the one place they're spelled. */
export const settingsKeys = {
  all: ['settings'] as const,
  /** The user's own: the model and effort their turns run on. */
  runSettings: ['settings', 'me'] as const,
};
