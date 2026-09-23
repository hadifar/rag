# Frontend

React + TypeScript chat UI for the RAG backend, built with Vite, [`@chatui/core`](https://github.com/alibaba/ChatUI), Tailwind CSS v4 and React Router.

## Install

```bash
npm install
```

## Run

```bash
npm run dev      # dev server with HMR
npm run build    # type-check and production build
npm run preview  # serve the production build
npm run lint     # oxlint
```

The dev server proxies `/api` (covering `/api/chat`, `/api/health`, `/api/kb`, `/api/settings`) to
the backend at `http://localhost:8000` (see [vite.config.ts](vite.config.ts)), so start the
backend first.

## Structure

```
src/
├── api/          # network calls (chat.ts streams SSE from /chat/stream)
├── components/
│   ├── layout/   # AppLayout, Sidebar (new chat, recent sessions, settings)
│   └── ...       # chat message renderers (tool, sources, avatars)
├── hooks/        # useChat: message state and streaming logic
├── pages/        # ChatPage, SettingsPage, NotFoundPage
├── types/        # shared types (chat events, Settings)
├── App.tsx       # router
└── main.tsx      # entry point
```

Routes: `/` (chat) and `/settings`. Any other path shows the 404 page.

## Notes

- **Styling:** Tailwind is loaded without its preflight reset, so it doesn't override `@chatui/core` styles. A small button/link reset lives in `@layer base` in [src/index.css](src/index.css). Chat bubble styles are in [src/App.css](src/App.css).
- **Typing indicator:** it is a real `typing` message added in `useChat`, because `@chatui/core`'s `isTyping` prop doesn't go through `renderMessageContent`.
- **New chat:** `ChatPage` is keyed on `location.key`, so navigating to `/` again remounts it with a fresh conversation and thread id.
- **Placeholders:** the recent sessions list in the sidebar is mock data, and the Settings page is a static template with no API yet.
