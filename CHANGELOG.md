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
