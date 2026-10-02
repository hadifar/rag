# Add an adapter

## Description

Wrap a third-party SDK client. Use when the backend needs a new external system.

## Steps

1. Define the port the services need in `rag/domain/ports/`.
2. Create `rag/adapters/<name>.py`. Implement the port.
3. If the client holds a connection, expose an async context manager: `open_<name>(settings)`.
4. Open the context manager in `build_container` in `rag/container.py`.
5. Pass the adapter to the service that needs the port.
6. Add a unit test with a fake, or an integration test in `tests/integration/`.
7. Validate the change. See [Run validation](../run-validation.md).

## Rules

* Only `rag/adapters/` imports third-party SDKs.
* Only `rag/container.py` constructs an adapter.
* Create a client once. Do not create a client per call.
* If configuration selects the backend, follow [Add configuration](add-configuration.md#add-a-backend-choice).

## Example

`open_db_pool` in `rag/adapters/postgres_db.py`, `open_archive_store` in `rag/adapters/kb_archive_store.py`.
