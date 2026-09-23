# Limitations — Production Readiness

## Data & ingestion
- `rag ingest` is a manual, one-shot CLI step — nothing triggers it on a doc change
- Re-ingesting never deletes vectors for removed source files
- `WholeDocumentChunker` puts an entire file into one record — no size-aware chunking for docs past the embedding model's input limit
- Only local markdown is supported — no PDF, Confluence, wiki, etc. loaders

## Retrieval

- Single fixed Pinecone namespace — no per-tenant/workspace isolation
- No reranker

## Conversation & session state

- `thread_id` is a client-supplied free string with no ownership check

## Security

- No authentication on any endpoint (`/chat/stream`, `/kb/*`, `/ui`)
- No CORS/security headers configured
- Dockerfile runs as root, uses a mutable base image tag, single-stage build

## Reliability

- No retry/backoff around Pinecone calls (LLM calls already retry with a fallback, see `graph.py`)
- `/health/ready` does a real embed + hybrid-search round trip on every hit
- Guardrail + verifier each add a full extra LLM call per turn, with no way to disable either


## Config & ops
- Single-process assumption throughout — won't survive multiple workers/replicas without a persistent checkpointer
