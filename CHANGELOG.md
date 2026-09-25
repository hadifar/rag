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
