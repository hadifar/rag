# Add a repository

## Description

Add SQL persistence behind a domain port. Use when a service needs a new table or new queries.

## Steps

1. Define a port in `rag/domain/ports/`. Example: `UserRepositoryPort`.
2. Create `rag/repository/<name>_repository.py`. Implement the port. Copy the shape of `rag/repository/user_repository.py`.
3. If the table is new, add a migration. See [Add a migration](add-migration.md).
4. Construct the repository with `db_pool` in `build_container` in `rag/container.py`.
5. Pass the repository to the service.
6. Add an integration test in `tests/integration/test_<name>_repository.py`.
7. Validate the change. See [Run validation](../run-validation.md).

## Rules

* A repository imports only `rag.domain` and its database client.
* Use `rag/adapters/` for SDK clients, not `rag/repository/`.
* Return domain models, not rows.
