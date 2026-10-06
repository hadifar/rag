# Add an agent capability

## Description

Give the chat agent a feature: tools plus prompt instructions. Use for features such as preferences, feedback or memory. Read [Chat agent](../../architecture/backend.md#chat-agent) first.

## Steps

1. Create or pick the service that owns the feature. See [Add a service](add-service.md).
2. Add a `capability()` method that returns a `Capability` (`rag/domain/models/agent/agent.py`). Copy `PreferenceService.capability()` in `rag/services/preference_service/service.py`.
3. Write each tool as a factory that closes over its dependencies and returns a domain `Tool`. Example: `search_tool` in `rag/services/rag_service/tools.py`.
4. Read the caller from the tool's `RunContext` argument.
5. Set `kind="user"` on a tool that acts on the user, not on the product.
6. To hand the user something beside the model's text, return it in `ToolResult.artifacts`. A new kind is a dataclass added to the `Artifact` union in `rag/domain/models/agent/artifact.py`, with its API model in `rag/api/schema/chat.py` and its bubble in `frontend/src/features/chat/model/transcript.ts`.
7. Pass the capability in `rag/container.py`: `RagService(capabilities=[...])`.
8. Add unit tests. Copy `tests/unit/test_preferences.py`.
9. Validate the change. See [Run validation](../run-validation.md).

## Rules

* Do not change `rag/services/agent_service/` to add a feature.
* Do not use a module-level `@tool` function or a global client.
* Do not take the user id from the model.
* Add a middleware spec only to change how the agent runs (a guard, planning).
