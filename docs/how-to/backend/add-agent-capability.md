# Add an agent capability

## Description

Give the chat agent a feature: tools plus prompt instructions. Use for features such as preferences, feedback or memory. Read [Chat agent](../../architecture/backend.md#chat-agent) first.

## Steps

1. Create or pick the service that owns the feature. See [Add a service](add-service.md). It holds the business rules and knows nothing of the agent.
2. Add a port in `rag/domain/ports/` with the methods the agent needs. Example: `PreferencesPort`, which `PreferenceService` satisfies.
3. Write the tools in `rag/services/agent_service/tools.py` as a factory that takes the port and returns LangChain tools made with `@tool`. Example: `preference_tools`.
4. Read the caller from an injected `runtime: ToolRuntime[RunContext]` argument (`runtime.context.user_id`). The model never sees it.
5. If a tool acts on the user, not on the product, add its name to `USER_TOOLS`. The off-topic guard keeps it, and the groundedness guard ignores its results.
6. For instructions on every model call, add them to `ChatAgent._system_prompt` in `rag/services/agent_service/agent.py`. Example: the preferences. Put prompt text in `rag/services/agent_service/prompts.py`.
7. To hand the user something beside the model's text, use `response_format="content_and_artifact"` and return the artifacts as JSON. Example: `search_tool`. A new kind is a dataclass added to the `Artifact` union in `rag/domain/models/agent/artifact.py`, with its API model in `rag/api/schema/chat.py` and its bubble in `frontend/src/features/chat/model/transcript.ts`.
8. Add the tools to `ChatAgent.__init__`, and pass the port to `ChatAgent` in `rag/container.py`.
9. Add tests in `tests/unit/test_chat_agent.py`. Copy the preference tests.
10. Validate the change. See [Run validation](../run-validation.md).

## Rules

* Do not import LangChain in the owning service.
* Do not use a module-level `@tool` function or a global client.
* Do not take the user id from the model.
