## v0.10.1 (2026-09-29)

### Refactor

- generation service into agent service and completion service
- merge ToolCallStart/ToolCallResult into one ToolCall event
- improve frontend architecture and error handling in components
- unify AuthenticatedIdentity usage across services and router
- repo reach only the domain
- drop langchain from domain.models
- add extra contract to ensure api follow our layering structure
- replace RagError with AppError across the codebase and update error handling
- add new contract to avoid importing domain via api/routers (only via dep & schema)
- update authentication handling to use AuthenticatedIdentity model

## v0.10.0 (2026-09-29)

### Feat

- **ci**: enforce frontend layering with oxlint and stricter tsc
- **ci**: enforce backend conventions with lint, types and an auth test
- **infra**: persist knowledge-base uploads in compose and Azure
- **frontend**: knowledge-base upload dialog on the Settings page
- **api**: admin knowledge-base upload with background ingestion runs
- **auth**: admin role for knowledge-base management
- **ingestion**: keep uploaded knowledge-base zips in archive storage
- **ingestion**: zip loader and hash-based index sync
- **chat**: shoSources none found when a knowledge-base search is empty

### Fix

- drop limit on chat
- **infra**: pass AUTH__JWT_SECRET to backend via Key Vault

### Refactor

- **ci**: enhance migration checks and enforce append-only policy
- **services**: generation depends on a SearchPort, not RetrievalService
- **frontend**: share load-on-mount and tidy useChat into steps
- **frontend**: move shared types out of hooks into types/
- **frontend**: mirror the backend's schemas one-to-one in types/api.ts
- **frontend**: derive text and sources bubble content from the API schema
- **api**: type the message stream's events through OpenAPI
- **api**: generate conversation titles on request, not in the stream
- **api**: keep deps.py to shared wiring and auth
- **api**: split chat into create-conversation and send-message endpoints
- **api**: native SSE, non-blocking hashing and router-level auth & take the refresh cookie lifetime from AuthService
- simplify ingestion loading, turns and defensive leftovers
- tidy CLI, user errors and small leftovers
- replace domain model conversions with Pydantic model validation across API responses
- **repository**: share row fetching through a BaseRepository
- name generation and retrieval dependencies after their services
- **generation**: move conversation titling into the generation service
- **dev**: fixed local Postgres creds and compose-side DATABASE_URL override
- **dev**: fixed local Postgres creds and compose-side DATABASE_URL override
- **config**: split DATABASE_URL into typed DATABASE__* settings with verified TLS by default
- update setup and configuration for improved testing and deployment

## v0.9.0 (2026-09-27)

### Feat

- use icon as favicon

### Refactor

- move chat comps into components/chat/ folder
- simplify frontend structure and let the client create conversation ids
- **frontend**: use useTransition for login and load-more pending state
- memoize bubbles, hoist markdown components, lazy-load chat page
- **frontend**: use named exports everywhere
- **frontend**: split useChat into useMessageList and a pure bubble handler
- **frontend**: move data and action logic out of components into hooks
- clean up frontend
- **guards**: derive groundedness revisions from turn messages, drop before_agent
- update setup instructions and enhance knowledge base extraction in setup script
- frontend polished
- drop data in favor data.zip & update docs

## v0.8.1 (2026-09-27)

### Fix

- add data

## v0.8.0 (2026-09-27)

### Feat

- replace Pinecone with pgvector and use a single DATABASE_URL
- persist conversations with an owned list, history and delete
- init commit authentication service

### Fix

- add a dedicated rate-limit zone for login
- sync db & checkpointer, include check & open to db
- use asyncconnectionpool to handle auto recovery
- JSON-encode SSE text events so newlines survive
- always mark refresh cookie secure

### Refactor

- drop the in-memory checkpointer and refresh stale docs
- use react-agent instead of graph
- error handling leaned & app is now only composition
- move user repo to its own package
- authentication and router structure for improved clarity and functionality

## v0.7.0 (2026-09-25)

### Feat

- add openai_azure option as llm provider

### Fix

- fastapi code review-setting issue
- add more import-linter

### Refactor

- move pinecone to its own config
- update configuration
- use callable[str|none] for adapters

## v0.6.0 (2026-09-25)

### Feat

- assistant message renders code, md, etc
- add HomePage component and update routing; modify sidebar navigation and NotFoundPage link
- add pre-commit hook for unit tests to catch contract breaks early
- refactor event handling by centralizing event definitions in rag.domain.events
- create a contract between pydantic & typescript types to ensure consistency
- add baselogger as an onother option for observablity
- add async rule

### Fix

- composer font is aligned with reset of the app
- adjust assistant left padding
- drop stall coreui docs & configs
- tool results by default is collapsed
- add resources to graph state
- add headers to nginx to avoid attacks
- enhance backend security by implementing network isolation and updating service plan SKU

### Refactor

- export single Schemas alias instaed of handpick names
- enhance chat types and streamline streamChat function
- streamline API calls with centralized URL and JSON post handling
- improve user/assistant text bubble
- drop chatui
- add error handler (domain.errors)
- use secretStr instead of plain str
- use deps for settings
- add tag to apirouter & return healthresponse for health api
- modernize dependency injection in FastAPI routers
- update stal docs & drop ContinaerHandle class & use fastapi app.state

## v0.5.1 (2026-09-23)

### Fix

- drop data/ from docker

## v0.5.0 (2026-09-23)

### Feat

- implement CI workflow for building and pushing Docker images, update Azure Bicep configuration, and enhance nginx setup
- add rff rank fusion

## v0.4.4 (2026-09-22)

### Fix

- add sudo chown to bump

## v0.4.3 (2026-09-22)

### Fix

- update precommit-gitguard to version 0.1.3 and adjust fetch-depth in pre-commit workflow

## v0.4.2 (2026-09-22)

### Fix

- issue with precommit bump uv lock
- resolve merge conflict
- resolve pre-commit bump issue

## v0.4.1 (2026-09-22)

### Fix

- update uv.lock

## v0.4.0 (2026-09-22)

### Feat

- add postgress for checkpointer
- add rate limit to nginx
- add mock session to the sidebar
- nav item ui updated
- layout updated & Typing added
- typing input added to chatui
- drop gradio
- react v1

### Fix

- frontend auto-bump included
- add api/ to kb route in react
- setting values comes from api
- update docker & docker compse
- drop gitflow hook with remote version
- add adapter contract for import lint

### Refactor

- drop unnecessary docstring
- replace local loads with pinecone
- reaname ranking to retrieval

## v0.3.0 (2026-09-15)

### Feat

- new sessioin btn added to ui & memorysaver replace with InMemorySaver

### Fix

- only consider 3 topk

## v0.2.1 (2026-09-15)

### Fix

- rename config base url

## v0.2.0 (2026-09-15)

### Feat

- add langfuse
- add integration test for retrieval
- implement hybrid search & drop langchain-pinecone
- use whole page chunking
- init commit

### Fix

- fix docker issue

### Refactor

- move verifier & guardrail into guards/ & add retry feedback mechanism for sudden hiccups
- rename config vars & add screen shots for readme
- merge small modules
- drop unused variables
