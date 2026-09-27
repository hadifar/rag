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
npm test         # Vitest in watch mode (see Test below)
```

The dev server proxies `/api` (covering `/api/auth`, `/api/chat`, `/api/conversations`, `/api/health`,
`/api/kb`, `/api/settings`) to
the backend at `http://localhost:8000` (see [vite.config.ts](vite.config.ts)), so start the
backend first.

## Test

```bash
npm test                  # unit + integration (Vitest), watch mode
npx vitest run            # same, once
E2E_EMAIL=you@example.com E2E_PASSWORD=… npm run test:e2e   # end-to-end (Playwright)
```

| Suite | Where | Runs against |
|---|---|---|
| Unit | `tests/unit/` | pure helpers and single components, in jsdom |
| Integration | `tests/integration/` | a whole page with the real hooks and API client; only the backend is faked, with [MSW](https://mswjs.io) ([tests/server.ts](tests/server.ts)) |
| E2E | `tests/e2e/` | the real stack in Chromium: Vite + backend + Postgres + the LLM |

Unit and integration tests use React Testing Library: find elements the way a user would (role,
label, text) and drive them with `user-event`. Fake the backend with `server.use(...)` rather than
mocking the app's own modules; a request with no handler fails the test.

The e2e suite signs in as an existing user (`uv run rag create-user`), passed via `E2E_EMAIL` /
`E2E_PASSWORD`. Playwright reuses a running backend (`:8000`) and dev server (`:5173`), or starts
them itself (always in CI) — the backend still needs Postgres, migrations and a filled `../.env`.
The first time, install the browser with `npx playwright install chromium`.

## Structure

```
src/
├── api/          # network calls (chat.ts streams SSE from /api/chat/stream; conversations.ts)
├── components/
│   ├── layout/   # AppLayout, RequireAuth, Sidebar (new chat, your conversations, settings)
│   └── chat/     # MessageList, Composer, and the text/tool/sources/typing bubbles it renders
├── context/      # AuthProvider (session), ConversationsProvider (sidebar list, paging, delete)
├── hooks/        # useChat (streaming, loading a conversation's history), useAuth/useConversations, …
├── pages/        # HomePage, ChatPage, LoginPage, SettingsPage, NotFoundPage
├── types/        # import from `types/`: api.ts (backend Schemas), chat.ts (messages/events), api.generated.ts
├── utils/        # pure helpers: conversation list updates, history → message bubbles
├── App.tsx       # router
└── main.tsx      # entry point

tests/
├── unit/         # mirrors src/ (utils/, components/)
├── integration/  # pages rendered with a fake backend
├── e2e/          # Playwright specs, auth.ts sign-in helper
├── server.ts     # MSW fake backend + sse() helper for streamed responses
└── setup.ts      # Vitest setup: jest-dom matchers, starts/resets the fake backend
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
- **Conversations:** a new chat gets its id from the client on its first message
  (`crypto.randomUUID()`), sent as `conversation_id`; `useChat` switches the URL to `/chat/:id`
  before anything streams, without remounting (so the answer keeps streaming). Any real navigation (sidebar, New chat, back)
  aborts the current stream and loads the target conversation's history.
- **Placeholders:** the Settings page is a static template with no write API yet — its Save
  button doesn't persist anything.
