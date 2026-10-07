/** The cache keys of chat data; the one place they're spelled. */
export const chatKeys = {
  /** A conversation's transcript; `undefined` is a new chat that has no id yet. */
  transcript: (conversationId: string | undefined) =>
    ['chat', 'transcript', conversationId ?? 'new'] as const,
  /** A conversation's own fields (e.g. its model and effort). */
  conversation: (conversationId: string) => ['chat', 'conversation', conversationId] as const,
  /** An attachment's content, as a data URL. */
  attachment: (conversationId: string, attachmentId: string) =>
    ['chat', 'attachment', conversationId, attachmentId] as const,
  /** A shared conversation, by its link's id. */
  shared: (shareId: string) => ['chat', 'shared', shareId] as const,
};
