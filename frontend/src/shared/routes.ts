/**
 * The app's URLs, spelled once: links and redirects build them here, and app/App.tsx
 * declares its routes from the same patterns, so the two can't drift apart.
 */
export const routes = {
  home: '/',
  login: '/login',
  settings: '/settings',
  /** A new chat, with no conversation yet. */
  newChat: '/chat',
  chat: (conversationId: string) => `/chat/${encodeURIComponent(conversationId)}`,
};

/** The route patterns, with their params, for the router and `useMatch`. */
export const routePatterns = {
  /** A new chat (`/chat`) or an existing one (`/chat/:conversationId`). */
  chat: '/chat/:conversationId?',
};
