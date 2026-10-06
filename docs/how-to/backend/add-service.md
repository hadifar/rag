# Add a service

## Description

Add a backend service, or add a method to one. Use for new business logic.

## Steps

1. If an existing service owns the area, add a method there and skip to step 5.
2. Create `rag/services/<name>_service/service.py` with one class.
3. Take every dependency as a `Protocol` from `rag/domain/ports/` in the constructor.
4. If the port does not exist, add it to the matching module in `rag/domain/ports/`.
5. Raise `AppError` subclasses from `rag/domain/errors.py` on failure.
6. Construct the service in `build_container` in `rag/container.py`. Add it as a field on `Container`.
7. If a router needs the service, add a getter and an alias in `rag/api/deps.py`.
8. Add unit tests in `tests/unit/`. Use the fakes in `tests/unit/fakes.py`.
9. Validate the change. See [Run validation](../run-validation.md).

## Rules

* Do not import another service. Depend on a port: `ChatAgentPort`, `LLMServicePort`, `SearchPort`.
* Do not import LangChain outside `rag/services/agent_service/`.
* Do not construct an adapter or a repository inside a service.
* Check ownership of a user-owned resource in the service. Return the same not-found error for a missing resource and another user's resource. Example: `ConversationService.get_owned`.
* Add a new variant as a new class that satisfies a port. Do not branch on type with `if kind == ...` or `isinstance`.
