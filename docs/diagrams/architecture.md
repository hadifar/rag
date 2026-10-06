# Architecture

System overview, backend layers and frontend layers.

## System overview

```mermaid
graph LR
    subgraph browser[Browser]
        ui[React app]
    end

    subgraph frontendc["frontend container (nginx)"]
        static[Static build]
        proxy["/api/* proxy"]
    end

    subgraph backendc["backend container (FastAPI)"]
        api[rag/api routers]
        agent["chat agent<br/>model ⇄ tools + guards"]
    end

    postgres[(Postgres + pgvector)]
    archives[(Archive storage<br/>disk / Azure Blob)]
    llm[[LLM provider]]
    langfuse[[Langfuse<br/>optional]]

    ui -->|assets| static
    ui -->|fetch / SSE| proxy
    proxy --> api
    api -->|users, conversations, transcripts| postgres
    api -->|uploaded zips| archives
    api --> agent
    agent -->|search_kb| postgres
    agent -->|chat, embeddings| llm
    agent -.->|traces| langfuse
```

## Backend layers

Arrows point to the imported layer. `import-linter` enforces every arrow.

```mermaid
graph TD
    api[api]
    services[services]
    domain[domain]
    adapters[adapters]
    repository[repository]
    container[container.py]

    api -->|only via deps.py| services
    services --> domain
    services -.->|ports only| adapters
    services -.->|ports only| repository
    adapters --> domain
    repository --> domain
    container -->|constructs| adapters
    container -->|constructs| repository
    container -->|constructs| services
```

## Frontend layers

oxlint enforces every arrow. Other features reach a feature only through its `index.ts`.

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD
    app["app<br/>router, shell"]
    pages[pages]
    subgraph feature["features/&lt;name&gt;"]
        components[components]
        hooks[hooks / context]
        model[model]
        fapi[api]
    end
    subgraph shared[shared]
        ui[ui]
        client[api/client.ts]
        types[types]
    end
    backend[["backend /api/*"]]
    schema[["rag/api/schema/*.py"]]

    app --> pages
    app --> feature
    pages --> feature
    components --> hooks
    components --> ui
    hooks --> fapi
    hooks --> model
    fapi --> client
    client --> backend
    feature --> types
    schema -.->|build time| types
```
