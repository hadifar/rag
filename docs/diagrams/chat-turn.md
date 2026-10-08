# Chat turn

```mermaid
sequenceDiagram
    participant UI as Frontend (useSendMessage)
    participant R as conversation router
    participant CS as ChatService
    participant A as Chat agent
    participant KB as RetrievalService
    participant DB as Postgres
    participant LLM as LLM provider

    UI->>R: POST /api/chat/{id}
    R->>CS: send_message
    CS->>DB: load earlier turns' agent memory
    CS->>A: run turn (with that memory)
    A->>LLM: check_input (input guard)
    A->>LLM: research call (plan, searches)
    A->>KB: search_kb
    KB->>DB: vector search
    A->>LLM: research call ("Done.", not shown)
    A->>LLM: answer call (from the search results)
    A-->>CS: stream events
    CS-->>R: events
    R-->>UI: SSE data: {type, ...}
    A-->>UI: answer
    A-->>UI: artifacts (sources)
    CS->>DB: save turn and its agent memory to conversation_turns
```
