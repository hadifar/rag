/** The cache keys of conversation data; the one place they're spelled. */
export const conversationKeys = {
  list: ['conversations', 'list'] as const,
  pinned: ['conversations', 'pinned'] as const,
  /** A conversation's public link, or null. */
  share: (conversationId: string) => ['conversations', 'share', conversationId] as const,
};
