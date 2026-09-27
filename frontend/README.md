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

The dev server proxies `/api` (covering `/api/auth`, `/api/chat`, `/api/conversations`, `/api/health`,
`/api/kb`, `/api/settings`) to
the backend at `http://localhost:8000` (see [vite.config.ts](vite.config.ts)), so start the
backend first.

## Structure

```
src/
├── api/          # network calls (chat.ts streams SSE from /api/chat/stream; conversations.ts)
├── components/
│   ├── layout/   # AppLayout, RequireAuth, Sidebar (new chat, your conversations, settings)
│   └── ...       # MessageList, Composer, and the tool/sources/typing bubbles it renders
├── context/      # AuthProvider (session), ConversationsProvider (sidebar list, paging, delete)
├── hooks/        # useChat (streaming, loading a conversation's history), useAuth/useConversations, …
├── pages/        # HomePage, ChatPage, LoginPage, SettingsPage, NotFoundPage
├── types/        # import from `types/`: api.ts (backend Schemas), chat.ts (messages/events), api.generated.ts
├── utils/        # pure helpers: conversation list updates, history → message bubbles
├── App.tsx       # router
└── main.tsx      # entry point
```

Routes: `/login`, `/` (home), `/chat` (new chat), `/chat/:conversationId`, `/settings`. Any other
path shows the 404 page.

## Notes

- **Chat UI:** built in-house on plain Tailwind components (`MessageList`, `Composer`,
  `ToolBubble`, `SourcesBubble`, `TypingIndicator`) — no chat UI library. The frontend is a pure
  presenter: `useChat` assembles messages from the backend's SSE events, and the tool bubble
  renders whatever `query`/`output` the backend already computed rather than inspecting raw args.
- **Typing indicator:** a real `typing` message appended in `useChat` and removed once the first
  real event for that turn arrives.
- **Conversations:** a new chat has no id until its first message — the server creates it and
  sends the id as the stream's first event, and `useChat` switches the URL to `/chat/:id` without
  remounting (so the answer keeps streaming). Any real navigation (sidebar, New chat, back)
  aborts the current stream and loads the target conversation's history.
- **Placeholders:** the Settings page is a static template with no write API yet — its Save
  button doesn't persist anything.
