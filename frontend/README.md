# Frontend

React + TypeScript chat UI for the RAG backend, built with Vite, Tailwind CSS v4 and React Router.

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
│   └── ...       # MessageList, Composer, and the tool/sources/typing bubbles it renders
├── hooks/        # useMessageList (message list state), useChat (streaming + message assembly)
├── pages/        # HomePage, ChatPage, SettingsPage, NotFoundPage
├── types/        # shared types (chat messages/events, Settings)
├── App.tsx       # router
└── main.tsx      # entry point
```

Routes: `/` (home), `/chat`, `/settings`. Any other path shows the 404 page.

## Notes

- **Chat UI:** built in-house on plain Tailwind components (`MessageList`, `Composer`,
  `ToolBubble`, `SourcesBubble`, `TypingIndicator`) — no chat UI library. The frontend is a pure
  presenter: `useChat` assembles messages from the backend's SSE events, and the tool bubble
  renders whatever `query`/`output` the backend already computed rather than inspecting raw args.
- **Typing indicator:** a real `typing` message appended in `useChat` and removed once the first
  real event for that turn arrives.
- **New chat:** `ChatPage` is keyed on `location.key`, so navigating to `/chat` again remounts it
  with a fresh conversation and thread id.
- **Placeholders:** the recent sessions list in the sidebar is mock data, and the Settings page is
  a static template with no write API yet.
