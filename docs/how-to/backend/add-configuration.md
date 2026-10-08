# Add configuration

## Description

Add a setting, or a backend selected by a setting. Use when behavior must change per environment.

## Add a setting

1. Find the section module in `rag/config/`.
2. Add a typed field with a default and `Field` bounds. Example: `RETRIEVAL_CANDIDATES: int = Field(default=10, ge=1)`.
3. If no section fits, add a field to `Settings` in `rag/config/settings.py`.
4. Add the variable, commented out with its default, to `.example.env`.
5. Pass the value to the service constructor in `rag/container.py`.
6. If the setting is a secret, follow [Add a secret](add-secret.md).

## Add a backend choice

Use for `LLM`, `OBSERVABILITY`, `TELEMETRY`, `KB_STORAGE`.

1. Add a Pydantic model with a `BACKEND: Literal["<name>"]` field to the section module.
2. Add the model to the discriminated union in the same module.
3. Add one `case` to the single `match` in the adapter:
    * `build_llm` in `rag/adapters/lang_llm_client.py`;
    * `open_trace_config` in `rag/adapters/lang_observability.py`;
    * `instrument_app` in `rag/adapters/telemetry.py`;
    * `open_archive_store` in `rag/adapters/kb_archive_store.py`.
4. Add the variables to `.example.env`.
5. If Azure needs the backend, add the parameters to `infra/azure/main.bicep`.

## Rules

* Read configuration only through `Settings`. `os.environ` and `os.getenv` are banned.
* Name nested variables with `__`: `RETRIEVAL__RERANK_CANDIDATES`.
* Callers never branch on the active backend.
* `Settings` forbids unknown variables (`extra="forbid"`). Remove a deleted variable from `.env`.
