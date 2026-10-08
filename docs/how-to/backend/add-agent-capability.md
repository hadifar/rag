# Add an agent capability

## Description

Give the chat agent a feature: tools plus prompt instructions. Use for features such as feedback or memory. Read [Chat agent](../../architecture/backend.md#chat-agent) first.

## Steps

1. Create or pick the service that owns the feature. See [Add a service](add-service.md). It holds the business rules and knows nothing of the agent.
2. Add a port in `rag/domain/ports/` with the methods the agent needs.
3. Write the tools in `rag/services/agent_service/tools.py` (or the module of their feature, like the skill tools in `skills.py`) as a factory that takes the port and returns LangChain tools made with `@tool`. Example: `search_tool`.
4. If a tool acts for the caller, give the graph the turn's `RunContext`: `StateGraph(ChatState, context_schema=RunContext)` in `RagAgent.__init__`, and `context=ctx` in `RagAgent.stream`. Read it from an injected `runtime: ToolRuntime[RunContext]` argument (`runtime.context.user_id`). The model never sees it.
5. If a tool acts on the user, not on the product, bind it on the off-topic models too (`RagAgent._off_topic_models`), and leave its results out of the answer guard's context (`_collect_context` in `guards/answer.py`).
6. For instructions on every model call, add them to `system_prompt` in `rag/services/agent_service/prompts.py`, with the prompt text.
7. To hand the user something beside the model's text, use `response_format="content_and_artifact"` and return the artifacts as JSON. Example: `search_tool`. A new kind is a dataclass added to the `Artifact` union in `rag/domain/models/agent/artifact.py`, with its API model in `rag/api/schema/chat.py` and its bubble in `frontend/src/features/chat/model/transcript.ts`.
8. Add the tools to `RagAgent.__init__`, and pass the port to `RagAgent` in `rag/container.py`.
9. Add tests in `tests/unit/test_rag_agent.py`. Drive the agent with `_ScriptedChatModel`.
10. Validate the change. See [Run validation](../run-validation.md).

## Rules

* Do not import LangChain in the owning service.
* Do not use a module-level `@tool` function or a global client.
* Do not take the user id from the model.
